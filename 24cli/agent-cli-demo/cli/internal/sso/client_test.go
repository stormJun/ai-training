package sso

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestLoginFlowExchangesApprovedDeviceCode(t *testing.T) {
	mux := http.NewServeMux()
	mux.HandleFunc("/sso/device/code", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"device_code":"dev_123","user_code":"USER-123","verification_uri":"http://127.0.0.1:8787/mock/approve?user_code=USER-123","expires_in":60,"interval":0}`))
	})

	pollCount := 0
	mux.HandleFunc("/sso/device/token", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		pollCount++
		if pollCount == 1 {
			w.WriteHeader(http.StatusPreconditionRequired)
			_, _ = w.Write([]byte(`{"error":"authorization_pending","message":"waiting for approval"}`))
			return
		}

		_, _ = w.Write([]byte(`{"access_token":"token_123","expires_at":"2026-06-12T20:00:00Z","user":{"id":"demo-user","name":"Demo User"}}`))
	})

	server := httptest.NewServer(mux)
	defer server.Close()

	cli := NewClient(server.URL)
	result, err := cli.Login(context.Background(), "mp-sso-cli")
	if err != nil {
		t.Fatalf("Login() error = %v", err)
	}

	if result.Token.AccessToken != "token_123" {
		t.Fatalf("Login() token = %q", result.Token.AccessToken)
	}

	if result.DeviceCode.UserCode != "USER-123" {
		t.Fatalf("Login() user code = %q", result.DeviceCode.UserCode)
	}
}
