package admin

import (
	"context"
	"encoding/json"
	"net/http"
	"strings"
	"time"
)

type Summary struct {
	PendingReviews int `json:"pending_reviews"`
	PublishedItems int `json:"published_items"`
	TodayVisits    int `json:"today_visits"`
}

type dashboardSummaryResponse struct {
	Summary Summary `json:"summary"`
}

type ResponseError struct {
	StatusCode int
	Message    string
}

func (e *ResponseError) Error() string {
	return e.Message
}

type Client struct {
	baseURL string
	token   string
	http    *http.Client
}

func NewClient(baseURL, token string) *Client {
	return &Client{
		baseURL: strings.TrimRight(baseURL, "/"),
		token:   token,
		http:    &http.Client{Timeout: 10 * time.Second},
	}
}

func (c *Client) FetchDashboardSummary(ctx context.Context) (Summary, error) {
	req, err := http.NewRequestWithContext(ctx, http.MethodGet, c.baseURL+"/api/dashboard/summary", nil)
	if err != nil {
		return Summary{}, err
	}

	if c.token != "" {
		req.Header.Set("Authorization", "Bearer "+c.token)
	}

	resp, err := c.http.Do(req)
	if err != nil {
		return Summary{}, err
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		var payload struct {
			Message string `json:"message"`
		}
		if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
			return Summary{}, err
		}
		return Summary{}, &ResponseError{
			StatusCode: resp.StatusCode,
			Message:    payload.Message,
		}
	}

	var payload dashboardSummaryResponse
	if err := json.NewDecoder(resp.Body).Decode(&payload); err != nil {
		return Summary{}, err
	}

	return payload.Summary, nil
}
