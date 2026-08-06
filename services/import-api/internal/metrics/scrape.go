package metrics

import (
	"crypto/sha256"
	"crypto/subtle"
	"errors"
	"net/http"
	"strings"
)

const (
	minimumScrapeTokenLength = 32
	maximumScrapeTokenLength = 256
	defaultScrapeMaxBytes    = 4 << 20
	prometheusContentType    = "text/plain; version=0.0.4; charset=utf-8"
)

var (
	ErrScrapeExporterRequired = errors.New("metrics scrape exporter is required")
	ErrScrapeTokenInvalid     = errors.New("metrics scrape token is invalid")
	ErrScrapeMaxBytesInvalid  = errors.New("metrics scrape maximum response size is invalid")
)

// PrometheusExporter is the narrow interface required by the scrape handler.
// Registry implements it. No business service receives this interface.
type PrometheusExporter interface {
	Prometheus() string
}

// ScrapeConfig configures a deliberately separate operational boundary. The
// handler is not mounted automatically; a deployment must explicitly wire it
// on a private listener or protected route.
type ScrapeConfig struct {
	Exporter PrometheusExporter
	// BearerToken must be a high-entropy deployment secret. It is never logged,
	// returned, used as a metric label or retained outside this configuration.
	BearerToken string
	// MaxResponseBytes bounds the in-memory exposition response. Zero selects
	// the conservative default.
	MaxResponseBytes int
}

// NewScrapeHandler constructs an authenticated Prometheus text endpoint. It
// fails closed when the exporter, token or response bound is invalid.
func NewScrapeHandler(config ScrapeConfig) (http.Handler, error) {
	if config.Exporter == nil {
		return nil, ErrScrapeExporterRequired
	}
	if !validScrapeToken(config.BearerToken) {
		return nil, ErrScrapeTokenInvalid
	}
	maxBytes := config.MaxResponseBytes
	if maxBytes == 0 {
		maxBytes = defaultScrapeMaxBytes
	}
	if maxBytes < 1024 || maxBytes > 16<<20 {
		return nil, ErrScrapeMaxBytesInvalid
	}

	expectedDigest := sha256.Sum256([]byte(config.BearerToken))
	return http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		writer.Header().Set("Cache-Control", "no-store")
		writer.Header().Set("X-Content-Type-Options", "nosniff")

		provided := scrapeBearerToken(request.Header.Get("Authorization"))
		providedDigest := sha256.Sum256([]byte(provided))
		if subtle.ConstantTimeCompare(providedDigest[:], expectedDigest[:]) != 1 {
			writer.Header().Set("WWW-Authenticate", `Bearer realm="metrics"`)
			http.Error(writer, "authentication required", http.StatusUnauthorized)
			return
		}
		if request.Method != http.MethodGet {
			writer.Header().Set("Allow", http.MethodGet)
			http.Error(writer, "method not allowed", http.StatusMethodNotAllowed)
			return
		}

		payload := config.Exporter.Prometheus()
		if len(payload) > maxBytes {
			http.Error(writer, "metrics unavailable", http.StatusServiceUnavailable)
			return
		}
		writer.Header().Set("Content-Type", prometheusContentType)
		writer.WriteHeader(http.StatusOK)
		_, _ = writer.Write([]byte(payload))
	}), nil
}

func validScrapeToken(token string) bool {
	if len(token) < minimumScrapeTokenLength || len(token) > maximumScrapeTokenLength {
		return false
	}
	for _, r := range token {
		if r <= 0x20 || r == 0x7f {
			return false
		}
	}
	return true
}

func scrapeBearerToken(header string) string {
	const prefix = "Bearer "
	if len(header) <= len(prefix) || len(header) > 512 || !strings.HasPrefix(header, prefix) {
		return ""
	}
	return header[len(prefix):]
}
