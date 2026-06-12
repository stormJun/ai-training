package command

import (
	"bytes"
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"agent-cli-demo/cli/internal/config"
)

func TestSSOLoginStatusAndLogout(t *testing.T) {
	t.Setenv("AGENT_CLI_DEMO_HOME", t.TempDir())

	pollCount := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch r.URL.Path {
		case "/sso/device/code":
			_, _ = w.Write([]byte(`{"device_code":"dev_123","user_code":"USER-123","verification_uri":"http://127.0.0.1:8787/mock/approve?user_code=USER-123","expires_in":60,"interval":0}`))
		case "/sso/device/token":
			pollCount++
			if pollCount == 1 {
				w.WriteHeader(http.StatusPreconditionRequired)
				_, _ = w.Write([]byte(`{"error":"authorization_pending","message":"waiting for approval"}`))
				return
			}
			_, _ = w.Write([]byte(`{"access_token":"token_123","expires_at":"2026-06-12T20:00:00Z","user":{"id":"demo-user","name":"Demo User"}}`))
		default:
			t.Fatalf("unexpected path %s", r.URL.Path)
		}
	}))
	defer server.Close()

	var loginStdout bytes.Buffer
	var loginStderr bytes.Buffer
	loginCode := ExecuteSSO(context.Background(), []string{"login", "--server", server.URL}, &loginStdout, &loginStderr)
	if loginCode != 0 {
		t.Fatalf("login exit code = %d, stderr = %s, stdout = %s", loginCode, loginStderr.String(), loginStdout.String())
	}

	var loginPayload struct {
		Status   string      `json:"status"`
		LoggedIn bool        `json:"logged_in"`
		Server   string      `json:"server"`
		User     config.User `json:"user"`
	}
	if err := json.Unmarshal(loginStdout.Bytes(), &loginPayload); err != nil {
		t.Fatalf("unmarshal login output: %v", err)
	}

	if !loginPayload.LoggedIn || loginPayload.User.ID != "demo-user" {
		t.Fatalf("unexpected login payload: %+v", loginPayload)
	}

	var statusStdout bytes.Buffer
	statusCode := ExecuteSSO(context.Background(), []string{"status"}, &statusStdout, &bytes.Buffer{})
	if statusCode != 0 {
		t.Fatalf("status exit code = %d", statusCode)
	}

	var statusPayload struct {
		LoggedIn bool   `json:"logged_in"`
		Server   string `json:"server"`
	}
	if err := json.Unmarshal(statusStdout.Bytes(), &statusPayload); err != nil {
		t.Fatalf("unmarshal status output: %v", err)
	}

	if !statusPayload.LoggedIn || statusPayload.Server != server.URL {
		t.Fatalf("unexpected status payload: %+v", statusPayload)
	}

	var logoutStdout bytes.Buffer
	logoutCode := ExecuteSSO(context.Background(), []string{"logout"}, &logoutStdout, &bytes.Buffer{})
	if logoutCode != 0 {
		t.Fatalf("logout exit code = %d", logoutCode)
	}

	cfg, err := config.Load()
	if err != nil {
		t.Fatalf("load config after logout: %v", err)
	}

	if cfg.Token.AccessToken != "" {
		t.Fatalf("token should be cleared after logout, got %q", cfg.Token.AccessToken)
	}
}
