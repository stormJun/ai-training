package config

import (
	"os"
	"path/filepath"
	"testing"
)

func TestSaveLoadAndClear(t *testing.T) {
	t.Setenv("AGENT_CLI_DEMO_HOME", t.TempDir())

	cfg := Config{
		ServerURL: "http://127.0.0.1:8787",
		Token: Token{
			AccessToken: "token_123",
			ExpiresAt:   "2026-06-12T20:00:00Z",
			User: User{
				ID:   "demo-user",
				Name: "Demo User",
			},
		},
	}

	if err := Save(cfg); err != nil {
		t.Fatalf("Save() error = %v", err)
	}

	loaded, err := Load()
	if err != nil {
		t.Fatalf("Load() error = %v", err)
	}

	if loaded.ServerURL != cfg.ServerURL {
		t.Fatalf("Load() server = %q, want %q", loaded.ServerURL, cfg.ServerURL)
	}

	if loaded.Token.AccessToken != cfg.Token.AccessToken {
		t.Fatalf("Load() token = %q, want %q", loaded.Token.AccessToken, cfg.Token.AccessToken)
	}

	path, err := Path()
	if err != nil {
		t.Fatalf("Path() error = %v", err)
	}

	if filepath.Dir(path) != filepath.Join(os.Getenv("AGENT_CLI_DEMO_HOME"), "data") {
		t.Fatalf("Path() dir = %q", filepath.Dir(path))
	}

	if err := ClearTokens(); err != nil {
		t.Fatalf("ClearTokens() error = %v", err)
	}

	cleared, err := Load()
	if err != nil {
		t.Fatalf("Load() after clear error = %v", err)
	}

	if cleared.Token.AccessToken != "" {
		t.Fatalf("token should be empty after clear, got %q", cleared.Token.AccessToken)
	}
}
