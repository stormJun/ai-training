package sso

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"strings"
	"time"

	"agent-cli-demo/cli/internal/config"
)

type DeviceCode struct {
	DeviceCode      string `json:"device_code"`
	UserCode        string `json:"user_code"`
	VerificationURI string `json:"verification_uri"`
	ExpiresIn       int    `json:"expires_in"`
	Interval        int    `json:"interval"`
}

type LoginResult struct {
	DeviceCode DeviceCode
	Token      config.Token
}

type Client struct {
	baseURL string
	http    *http.Client
}

func NewClient(baseURL string) *Client {
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		http:    &http.Client{Timeout: 10 * time.Second},
	}
}

func (c *Client) Login(ctx context.Context, clientID string) (LoginResult, error) {
	deviceCode, err := c.RequestDeviceCode(ctx, clientID)
	if err != nil {
		return LoginResult{}, err
	}

	token, err := c.WaitForToken(ctx, clientID, deviceCode)
	if err != nil {
		return LoginResult{}, err
	}

	return LoginResult{
		DeviceCode: deviceCode,
		Token:      token,
	}, nil
}

func (c *Client) WaitForToken(ctx context.Context, clientID string, deviceCode DeviceCode) (config.Token, error) {
	interval := deviceCode.Interval
	if interval <= 0 {
		interval = 1
	}

	deadline := time.Now().Add(time.Duration(deviceCode.ExpiresIn) * time.Second)
	for {
		token, pending, err := c.pollToken(ctx, clientID, deviceCode.DeviceCode)
		if err != nil {
			return config.Token{}, err
		}

		if !pending {
			return token, nil
		}

		if time.Now().After(deadline) {
			return config.Token{}, fmt.Errorf("device authorization expired")
		}

		select {
		case <-ctx.Done():
			return config.Token{}, ctx.Err()
		case <-time.After(time.Duration(interval) * time.Second):
		}
	}
}

func (c *Client) RequestDeviceCode(ctx context.Context, clientID string) (DeviceCode, error) {
	body, err := json.Marshal(map[string]string{
		"client_id": clientID,
	})
	if err != nil {
		return DeviceCode{}, err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/sso/device/code", bytes.NewReader(body))
	if err != nil {
		return DeviceCode{}, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.http.Do(req)
	if err != nil {
		return DeviceCode{}, err
	}
	defer resp.Body.Close()

	var deviceCode DeviceCode
	if err := json.NewDecoder(resp.Body).Decode(&deviceCode); err != nil {
		return DeviceCode{}, err
	}

	if resp.StatusCode != http.StatusOK {
		return DeviceCode{}, fmt.Errorf("request device code failed with status %d", resp.StatusCode)
	}

	return deviceCode, nil
}

func (c *Client) pollToken(ctx context.Context, clientID, deviceCode string) (config.Token, bool, error) {
	body, err := json.Marshal(map[string]string{
		"client_id":   clientID,
		"device_code": deviceCode,
	})
	if err != nil {
		return config.Token{}, false, err
	}

	req, err := http.NewRequestWithContext(ctx, http.MethodPost, c.baseURL+"/sso/device/token", bytes.NewReader(body))
	if err != nil {
		return config.Token{}, false, err
	}
	req.Header.Set("Content-Type", "application/json")

	resp, err := c.http.Do(req)
	if err != nil {
		return config.Token{}, false, err
	}
	defer resp.Body.Close()

	if resp.StatusCode == http.StatusPreconditionRequired {
		return config.Token{}, true, nil
	}

	var token config.Token
	if err := json.NewDecoder(resp.Body).Decode(&token); err != nil {
		return config.Token{}, false, err
	}

	if resp.StatusCode != http.StatusOK {
		return config.Token{}, false, fmt.Errorf("poll token failed with status %d", resp.StatusCode)
	}

	return token, false, nil
}
