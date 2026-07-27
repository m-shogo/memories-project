package ratelimit

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"net"
	"net/netip"
	"strings"
)

// KeyDeriver turns a request's transport address (and, only when a trusted
// proxy boundary is configured, a forwarded header) into an opaque, non-secret
// rate-limit key. The raw address is never stored or logged: it is normalized
// to a network prefix and then HMAC'd with a rotating secret, so the key is a
// short-lived digest that cannot be reversed to an address and is not a durable
// user identifier.
//
// Trusted-proxy boundary: by default no proxy is trusted, so the transport
// RemoteAddr is authoritative and any X-Forwarded-For is ignored. A deployment
// behind a known proxy sets TrustedProxies to that proxy's CIDRs; only then is
// the right-most forwarded hop that is not itself a trusted proxy taken as the
// client. An arbitrary client-supplied X-Forwarded-For is never trusted.
type KeyDeriver struct {
	// Secret keys the HMAC. Rotating it rotates every derived key, which is why
	// a digest must never be used as a durable identifier — it changes on
	// rotation by design.
	Secret []byte
	// TrustedProxies is the set of proxy networks whose forwarded headers may be
	// believed. Empty means trust none.
	TrustedProxies []netip.Prefix
	// IPv6PrefixBits is the network prefix IPv6 addresses are masked to before
	// hashing, so a single client cannot evade limits by rotating through the
	// many addresses in its /64 (IPv6 privacy addresses). Defaults to 64.
	IPv6PrefixBits int
}

// ParseTrustedProxies parses a comma-separated CIDR list. An empty string
// yields an empty (trust-none) set. A malformed entry is an error, so a
// misconfigured proxy list fails at startup rather than silently trusting
// nothing or everything.
func ParseTrustedProxies(list string) ([]netip.Prefix, error) {
	list = strings.TrimSpace(list)
	if list == "" {
		return nil, nil
	}
	var prefixes []netip.Prefix
	for _, item := range strings.Split(list, ",") {
		prefix, err := netip.ParsePrefix(strings.TrimSpace(item))
		if err != nil {
			return nil, err
		}
		prefixes = append(prefixes, prefix)
	}
	return prefixes, nil
}

// NetworkKey derives the opaque per-network key. remoteAddr is the transport
// address (host:port, as in http.Request.RemoteAddr); forwardedFor is the raw
// X-Forwarded-For header value, honored only through the trusted-proxy boundary.
// The returned key is prefixed so it is recognizable in a store as a network
// key, and it contains only a hex digest — never the address.
func (d KeyDeriver) NetworkKey(remoteAddr, forwardedFor string) string {
	client := d.clientAddr(remoteAddr, forwardedFor)
	if !client.IsValid() {
		// An unparseable or missing address collapses to one fixed bucket, so
		// such requests are still bounded as a group rather than escaping limits.
		return "net_unknown"
	}
	network := d.maskToNetwork(client)
	prefixBits := d.IPv6PrefixBits
	if prefixBits <= 0 || prefixBits > 128 {
		prefixBits = 64
	}
	// Domain-separate the HMAC input with the address family and prefix so an
	// IPv4 /32 and an IPv6 /64 can never collide.
	material := network.String()
	digest := d.digest("net", material)
	return "net_" + digest
}

// clientAddr resolves the client address, applying the trusted-proxy boundary.
func (d KeyDeriver) clientAddr(remoteAddr, forwardedFor string) netip.Addr {
	transport := parseHostAddr(remoteAddr)
	if len(d.TrustedProxies) == 0 || !d.isTrusted(transport) {
		// No trusted proxy, or the immediate peer is not a trusted proxy: the
		// transport peer is the client and forwarded headers are ignored.
		return transport
	}
	// The immediate peer is a trusted proxy. Walk the forwarded chain from the
	// right, skipping trusted proxies, and take the first untrusted hop as the
	// client. If every hop is trusted or the header is empty, fall back to the
	// transport peer.
	hops := strings.Split(forwardedFor, ",")
	for i := len(hops) - 1; i >= 0; i-- {
		candidate := parseHostAddr(strings.TrimSpace(hops[i]))
		if !candidate.IsValid() {
			continue
		}
		if d.isTrusted(candidate) {
			continue
		}
		return candidate
	}
	return transport
}

func (d KeyDeriver) isTrusted(addr netip.Addr) bool {
	if !addr.IsValid() {
		return false
	}
	for _, prefix := range d.TrustedProxies {
		if prefix.Contains(addr) {
			return true
		}
	}
	return false
}

// maskToNetwork reduces an address to the network a limit should apply to: the
// full /32 for IPv4 (one address is one client), and a /IPv6PrefixBits prefix
// for IPv6 (so address rotation within a client's allocation does not evade the
// limit).
func (d KeyDeriver) maskToNetwork(addr netip.Addr) netip.Prefix {
	if addr.Is4() || addr.Is4In6() {
		v4 := addr.Unmap()
		return netip.PrefixFrom(v4, 32)
	}
	bits := d.IPv6PrefixBits
	if bits <= 0 || bits > 128 {
		bits = 64
	}
	prefix, err := addr.Prefix(bits)
	if err != nil {
		return netip.PrefixFrom(addr, 128)
	}
	return prefix
}

// RouteKey derives the route-wide global guard key: one bucket per route
// template, independent of source, so a route cannot be flooded from many
// sources below the per-network threshold.
func (d KeyDeriver) RouteKey(routeTemplate string) string {
	return "route_" + d.digest("route", routeTemplate)
}

// digest HMACs the domain-separated material. Without a secret it still returns
// a stable hash so the limiter degrades to deterministic (if unkeyed) keys
// rather than failing; a real deployment always sets a secret.
func (d KeyDeriver) digest(domain, material string) string {
	mac := hmac.New(sha256.New, d.Secret)
	mac.Write([]byte(domain))
	mac.Write([]byte{0x1f})
	mac.Write([]byte(material))
	sum := mac.Sum(nil)
	// 16 bytes of the digest is ample to separate keys and keeps the key short.
	return hex.EncodeToString(sum[:16])
}

func parseHostAddr(hostPort string) netip.Addr {
	hostPort = strings.TrimSpace(hostPort)
	if hostPort == "" {
		return netip.Addr{}
	}
	// RemoteAddr is host:port; a forwarded hop is usually a bare address. Try
	// splitting a port first, then fall back to the whole string.
	if host, _, err := net.SplitHostPort(hostPort); err == nil {
		hostPort = host
	}
	// Strip an IPv6 zone if present.
	if i := strings.IndexByte(hostPort, '%'); i >= 0 {
		hostPort = hostPort[:i]
	}
	addr, err := netip.ParseAddr(hostPort)
	if err != nil {
		return netip.Addr{}
	}
	return addr
}
