package httpserver

import (
	"context"
	"errors"
	"io"
	"net"
	"net/http"
	"testing"
	"time"
)

// TestHTTPServerGracefulInterruptionDrainsInFlightRequest exercises a real TCP
// listener. Shutdown must stop accepting new work, wait for the active request,
// preserve its response, and then leave the endpoint unreachable.
func TestHTTPServerGracefulInterruptionDrainsInFlightRequest(t *testing.T) {
	started := make(chan struct{})
	release := make(chan struct{})
	handler := http.HandlerFunc(func(writer http.ResponseWriter, request *http.Request) {
		close(started)
		select {
		case <-release:
			writer.WriteHeader(http.StatusOK)
			_, _ = writer.Write([]byte("drained"))
		case <-request.Context().Done():
			t.Errorf("in-flight request was canceled during graceful shutdown: %v", request.Context().Err())
		}
	})

	listener, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	server := NewHTTPServer(listener.Addr().String(), handler)
	serveResult := make(chan error, 1)
	go func() { serveResult <- server.Serve(listener) }()

	client := &http.Client{Timeout: 5 * time.Second}
	responseResult := make(chan error, 1)
	go func() {
		response, err := client.Get("http://" + listener.Addr().String() + "/")
		if err != nil {
			responseResult <- err
			return
		}
		defer response.Body.Close()
		body, err := io.ReadAll(response.Body)
		if err != nil {
			responseResult <- err
			return
		}
		if response.StatusCode != http.StatusOK || string(body) != "drained" {
			responseResult <- errors.New("gracefully drained request returned unexpected response")
			return
		}
		responseResult <- nil
	}()

	select {
	case <-started:
	case <-time.After(2 * time.Second):
		t.Fatal("request did not reach the server")
	}

	shutdownResult := make(chan error, 1)
	go func() {
		ctx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
		defer cancel()
		shutdownResult <- server.Shutdown(ctx)
	}()

	select {
	case err := <-shutdownResult:
		t.Fatalf("shutdown returned before the in-flight request completed: %v", err)
	case <-time.After(100 * time.Millisecond):
	}

	close(release)
	if err := <-responseResult; err != nil {
		t.Fatal(err)
	}
	if err := <-shutdownResult; err != nil {
		t.Fatalf("graceful shutdown failed: %v", err)
	}
	if err := <-serveResult; !errors.Is(err, http.ErrServerClosed) {
		t.Fatalf("Serve returned unexpected error: %v", err)
	}

	request, err := http.NewRequest(http.MethodGet, "http://"+listener.Addr().String()+"/", nil)
	if err != nil {
		t.Fatal(err)
	}
	if response, err := client.Do(request); err == nil {
		response.Body.Close()
		t.Fatal("server accepted a new request after shutdown")
	}
}
