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

func TestAdminDashboardSummaryRequiresLogin(t *testing.T) {
	t.Setenv("AGENT_CLI_DEMO_HOME", t.TempDir())

	var stdout bytes.Buffer
	code := ExecuteAdmin(context.Background(), []string{"dashboard", "summary", "--server", "http://127.0.0.1:8787"}, &stdout, &bytes.Buffer{})
	if code != 10 {
		t.Fatalf("exit code = %d, stdout = %s", code, stdout.String())
	}

	var payload struct {
		Error string `json:"error"`
	}
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatalf("unmarshal error payload: %v", err)
	}

	if payload.Error != "AUTH_REQUIRED" {
		t.Fatalf("unexpected payload: %+v", payload)
	}
}

func TestAdminDashboardSummarySuccess(t *testing.T) {
	t.Setenv("AGENT_CLI_DEMO_HOME", t.TempDir())

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/dashboard/summary" {
			t.Fatalf("unexpected path %s", r.URL.Path)
		}
		if got := r.Header.Get("Authorization"); got != "Bearer token_123" {
			t.Fatalf("authorization = %q", got)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"summary":{"pending_reviews":3,"published_items":12,"today_visits":248}}`))
	}))
	defer server.Close()

	if err := config.Save(config.Config{
		ServerURL: server.URL,
		Token: config.Token{
			AccessToken: "token_123",
			ExpiresAt:   "2026-06-12T20:00:00Z",
			User: config.User{
				ID:   "demo-user",
				Name: "Demo User",
			},
		},
	}); err != nil {
		t.Fatalf("save config: %v", err)
	}

	var stdout bytes.Buffer
	code := ExecuteAdmin(context.Background(), []string{"dashboard", "summary"}, &stdout, &bytes.Buffer{})
	if code != 0 {
		t.Fatalf("exit code = %d, stdout = %s", code, stdout.String())
	}

	var payload struct {
		Summary map[string]int `json:"summary"`
	}
	if err := json.Unmarshal(stdout.Bytes(), &payload); err != nil {
		t.Fatalf("unmarshal success payload: %v", err)
	}

	if payload.Summary["pending_reviews"] != 3 {
		t.Fatalf("unexpected payload: %+v", payload)
	}
}
