package ratelimit

import (
	"net/netip"
	"strings"
	"testing"
)

func deriver(t *testing.T, trusted string) KeyDeriver {
	t.Helper()
	prefixes, err := ParseTrustedProxies(trusted)
	if err != nil {
		t.Fatal(err)
	}
	return KeyDeriver{Secret: []byte("test-secret-key"), TrustedProxies: prefixes, IPv6PrefixBits: 64}
}

func TestForwardedHeaderIgnoredWithoutTrustedProxy(t *testing.T) {
	d := deriver(t, "")
	// Two requests from the same transport peer with different (untrusted)
	// X-Forwarded-For values must land in the SAME bucket: the header is ignored.
	a := d.NetworkKey("203.0.113.7:44321", "1.2.3.4")
	b := d.NetworkKey("203.0.113.7:44322", "9.9.9.9")
	if a != b {
		t.Fatalf("untrusted forwarded header changed the key: %s vs %s", a, b)
	}
	// A different real peer is a different bucket.
	c := d.NetworkKey("198.51.100.5:1000", "1.2.3.4")
	if c == a {
		t.Fatal("different peers collapsed to one key")
	}
}

func TestTrustedProxyUsesRightmostUntrustedHop(t *testing.T) {
	d := deriver(t, "10.0.0.0/8")
	// Peer is the trusted proxy; the forwarded chain ends with the real client
	// then the trusted proxy. The client is 203.0.113.9.
	key := d.NetworkKey("10.0.0.1:9999", "203.0.113.9, 10.0.0.2")
	direct := d.NetworkKey("203.0.113.9:5000", "")
	if key != direct {
		t.Fatalf("trusted proxy did not resolve the real client: %s vs %s", key, direct)
	}
	// A spoofed extra hop to the LEFT does not change the client, because we take
	// the right-most untrusted hop.
	spoofed := d.NetworkKey("10.0.0.1:9999", "6.6.6.6, 203.0.113.9, 10.0.0.2")
	if spoofed != direct {
		t.Fatalf("a left-side spoofed hop changed the client: %s", spoofed)
	}
}

func TestUntrustedPeerIgnoresForwardedEvenIfProxiesConfigured(t *testing.T) {
	d := deriver(t, "10.0.0.0/8")
	// The immediate peer is NOT a trusted proxy, so the forwarded header is not
	// believed even though a proxy list is configured.
	withHeader := d.NetworkKey("203.0.113.20:1234", "1.1.1.1")
	withoutHeader := d.NetworkKey("203.0.113.20:1234", "")
	if withHeader != withoutHeader {
		t.Fatal("forwarded header trusted from a non-proxy peer")
	}
}

func TestIPv6IsMaskedToPrefix(t *testing.T) {
	d := deriver(t, "")
	// Two addresses in the same /64 must share a bucket (privacy-address
	// rotation cannot evade the limit).
	a := d.NetworkKey("[2001:db8:abcd:1::1]:443", "")
	b := d.NetworkKey("[2001:db8:abcd:1::beef]:443", "")
	if a != b {
		t.Fatalf("same /64 produced different keys: %s vs %s", a, b)
	}
	// A different /64 is a different bucket.
	c := d.NetworkKey("[2001:db8:abcd:2::1]:443", "")
	if c == a {
		t.Fatal("different /64 collapsed to one key")
	}
}

func TestIPv4NormalizationIsStable(t *testing.T) {
	d := deriver(t, "")
	// An IPv4-mapped IPv6 form and the plain IPv4 form are the same client.
	plain := d.NetworkKey("203.0.113.30:80", "")
	mapped := d.NetworkKey("[::ffff:203.0.113.30]:80", "")
	if plain != mapped {
		t.Fatalf("ipv4 and ipv4-mapped forms differ: %s vs %s", plain, mapped)
	}
}

func TestMalformedOrMissingAddressCollapsesSafely(t *testing.T) {
	d := deriver(t, "")
	for _, bad := range []string{"", "not-an-address", "999.999.999.999:1", "garbage:port:extra"} {
		if key := d.NetworkKey(bad, ""); key != "net_unknown" {
			t.Fatalf("malformed address %q did not collapse safely: %s", bad, key)
		}
	}
}

func TestKeyNeverContainsRawAddress(t *testing.T) {
	d := deriver(t, "10.0.0.0/8")
	for _, addr := range []string{"203.0.113.44:1", "[2001:db8::1]:1"} {
		key := d.NetworkKey(addr, "198.51.100.9")
		for _, raw := range []string{"203.0.113.44", "2001:db8", "198.51.100.9"} {
			if strings.Contains(key, raw) {
				t.Fatalf("derived key leaked a raw address fragment %q: %s", raw, key)
			}
		}
	}
}

func TestKeyRotatesWithSecret(t *testing.T) {
	a := KeyDeriver{Secret: []byte("secret-a"), IPv6PrefixBits: 64}
	b := KeyDeriver{Secret: []byte("secret-b"), IPv6PrefixBits: 64}
	if a.NetworkKey("203.0.113.50:1", "") == b.NetworkKey("203.0.113.50:1", "") {
		t.Fatal("key did not change with the secret; a digest must not be a durable identifier")
	}
}

func TestParseTrustedProxiesRejectsMalformed(t *testing.T) {
	if _, err := ParseTrustedProxies("10.0.0.0/8, not-a-cidr"); err == nil {
		t.Fatal("malformed proxy list accepted")
	}
	got, err := ParseTrustedProxies("")
	if err != nil || len(got) != 0 {
		t.Fatalf("empty list should trust none: %v %v", got, err)
	}
	got, err = ParseTrustedProxies("10.0.0.0/8")
	if err != nil || len(got) != 1 || got[0] != netip.MustParsePrefix("10.0.0.0/8") {
		t.Fatalf("valid list parse: %v %v", got, err)
	}
}
