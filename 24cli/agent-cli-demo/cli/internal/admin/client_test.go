package admin

import (
	"context"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestFetchDashboardSummary(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if got := r.Header.Get("Authorization"); got != "Bearer token_123" {
			t.Fatalf("Authorization header = %q", got)
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(`{"summary":{"pending_reviews":3,"published_items":12,"today_visits":248}}`))
	}))
	defer server.Close()

	cli := NewClient(server.URL, "token_123")
	summary, err := cli.FetchDashboardSummary(context.Background())
	if err != nil {
		t.Fatalf("FetchDashboardSummary() error = %v", err)
	}

	if summary.PendingReviews != 3 || summary.PublishedItems != 12 || summary.TodayVisits != 248 {
		t.Fatalf("FetchDashboardSummary() = %+v", summary)
	}
}
