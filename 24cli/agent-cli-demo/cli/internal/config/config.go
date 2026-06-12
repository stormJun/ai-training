package config

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"path/filepath"
)

type User struct {
	ID   string `json:"id"`
	Name string `json:"name"`
}

type Token struct {
	AccessToken string `json:"access_token"`
	ExpiresAt   string `json:"expires_at"`
	User        User   `json:"user"`
}

type Config struct {
	ServerURL string `json:"server_url"`
	Token     Token  `json:"token"`
}

func Path() (string, error) {
	home := os.Getenv("AGENT_CLI_DEMO_HOME")
	if home == "" {
		userHome, err := os.UserHomeDir()
		if err != nil {
			return "", fmt.Errorf("resolve user home: %w", err)
		}
		home = filepath.Join(userHome, ".agent-cli-demo")
	}

	return filepath.Join(home, "data", "config.json"), nil
}

func Load() (Config, error) {
	path, err := Path()
	if err != nil {
		return Config{}, err
	}

	data, err := os.ReadFile(path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return Config{}, nil
		}
		return Config{}, fmt.Errorf("read config: %w", err)
	}

	var cfg Config
	if err := json.Unmarshal(data, &cfg); err != nil {
		return Config{}, fmt.Errorf("decode config: %w", err)
	}

	return cfg, nil
}

func Save(cfg Config) error {
	path, err := Path()
	if err != nil {
		return err
	}

	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return fmt.Errorf("create config dir: %w", err)
	}

	data, err := json.MarshalIndent(cfg, "", "  ")
	if err != nil {
		return fmt.Errorf("encode config: %w", err)
	}

	if err := os.WriteFile(path, data, 0o600); err != nil {
		return fmt.Errorf("write config: %w", err)
	}

	return nil
}

func ClearTokens() error {
	cfg, err := Load()
	if err != nil {
		return err
	}

	cfg.Token = Token{}
	return Save(cfg)
}
