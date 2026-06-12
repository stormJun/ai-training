package command

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"io"

	"agent-cli-demo/cli/internal/admin"
	"agent-cli-demo/cli/internal/clierr"
	"agent-cli-demo/cli/internal/config"
	"agent-cli-demo/cli/internal/sso"
	"github.com/spf13/cobra"
)

type jsonError struct {
	Error   string `json:"error"`
	Message string `json:"message"`
}

func ExecuteSSO(ctx context.Context, args []string, stdout, stderr io.Writer) int {
	var flagServer string

	root := &cobra.Command{
		Use:           "mp-sso-cli",
		SilenceUsage:  true,
		SilenceErrors: true,
	}

	loginCmd := &cobra.Command{
		Use: "login",
		RunE: func(cmd *cobra.Command, _ []string) error {
			cfg, err := config.Load()
			if err != nil {
				return clierr.New(clierr.ExitInternalError, "INTERNAL_ERROR", err.Error())
			}

			serverURL := firstNonEmpty(flagServer, cfg.ServerURL)
			if serverURL == "" {
				return clierr.New(clierr.ExitInvalidArgument, "INVALID_ARGUMENT", "server url required: pass --server URL")
			}

			client := sso.NewClient(serverURL)
			deviceCode, err := client.RequestDeviceCode(ctx, "mp-sso-cli")
			if err != nil {
				return clierr.New(clierr.ExitNetworkError, "NETWORK_ERROR", err.Error())
			}

			_, _ = fmt.Fprintf(stderr, "Open this URL in your browser:\n\n  %s\n\n", deviceCode.VerificationURI)
			_, _ = fmt.Fprintf(stderr, "Then enter this code:\n\n  %s\n\n", deviceCode.UserCode)
			_, _ = fmt.Fprintln(stderr, "Waiting for authorization...")

			token, err := client.WaitForToken(ctx, "mp-sso-cli", deviceCode)
			if err != nil {
				return clierr.New(clierr.ExitInternalError, "INTERNAL_ERROR", err.Error())
			}

			cfg.ServerURL = serverURL
			cfg.Token = token
			if err := config.Save(cfg); err != nil {
				return clierr.New(clierr.ExitInternalError, "INTERNAL_ERROR", err.Error())
			}

			return writeJSON(stdout, map[string]any{
				"status":       "ok",
				"logged_in":    true,
				"server":       serverURL,
				"user":         token.User,
				"token_cached": true,
			})
		},
	}
	loginCmd.Flags().StringVar(&flagServer, "server", "", "demo server url")

	statusCmd := &cobra.Command{
		Use: "status",
		RunE: func(cmd *cobra.Command, _ []string) error {
			cfg, err := config.Load()
			if err != nil {
				return clierr.New(clierr.ExitInternalError, "INTERNAL_ERROR", err.Error())
			}

			return writeJSON(stdout, map[string]any{
				"logged_in":        cfg.Token.AccessToken != "",
				"server":           cfg.ServerURL,
				"user":             cfg.Token.User,
				"token_expires_at": cfg.Token.ExpiresAt,
			})
		},
	}

	logoutCmd := &cobra.Command{
		Use: "logout",
		RunE: func(cmd *cobra.Command, _ []string) error {
			if err := config.ClearTokens(); err != nil {
				return clierr.New(clierr.ExitInternalError, "INTERNAL_ERROR", err.Error())
			}

			return writeJSON(stdout, map[string]any{
				"status":     "ok",
				"logged_out": true,
			})
		},
	}

	root.AddCommand(loginCmd, statusCmd, logoutCmd)
	root.SetArgs(args)

	return execute(root, stdout)
}

func ExecuteAdmin(ctx context.Context, args []string, stdout, stderr io.Writer) int {
	var flagServer string

	root := &cobra.Command{
		Use:           "mp-admin-cli",
		SilenceUsage:  true,
		SilenceErrors: true,
	}

	dashboardCmd := &cobra.Command{Use: "dashboard"}
	summaryCmd := &cobra.Command{
		Use: "summary",
		RunE: func(cmd *cobra.Command, _ []string) error {
			cfg, err := config.Load()
			if err != nil {
				return clierr.New(clierr.ExitInternalError, "INTERNAL_ERROR", err.Error())
			}

			serverURL := firstNonEmpty(flagServer, cfg.ServerURL)
			if serverURL == "" {
				return clierr.New(clierr.ExitInvalidArgument, "INVALID_ARGUMENT", "server url required: pass --server URL")
			}
			if cfg.Token.AccessToken == "" {
				return clierr.New(clierr.ExitAuthRequired, "AUTH_REQUIRED", "please run mp-sso-cli login")
			}

			client := admin.NewClient(serverURL, cfg.Token.AccessToken)
			summary, err := client.FetchDashboardSummary(ctx)
			if err != nil {
				var responseErr *admin.ResponseError
				if errors.As(err, &responseErr) {
					switch responseErr.StatusCode {
					case 401:
						return clierr.New(clierr.ExitAuthRequired, "AUTH_REQUIRED", "please run mp-sso-cli login")
					case 403:
						return clierr.New(clierr.ExitPermissionDenied, "PERMISSION_DENIED", "current user has no permission to access dashboard summary")
					}
				}
				return clierr.New(clierr.ExitInternalError, "INTERNAL_ERROR", err.Error())
			}

			return writeJSON(stdout, map[string]any{
				"summary": summary,
			})
		},
	}
	summaryCmd.Flags().StringVar(&flagServer, "server", "", "demo server url")
	dashboardCmd.AddCommand(summaryCmd)
	root.AddCommand(dashboardCmd)
	root.SetArgs(args)

	_ = stderr
	return execute(root, stdout)
}

func execute(root *cobra.Command, stdout io.Writer) int {
	if err := root.Execute(); err != nil {
		var cliError *clierr.Error
		if errors.As(err, &cliError) {
			_ = writeJSON(stdout, jsonError{
				Error:   cliError.Name,
				Message: cliError.Message,
			})
			return cliError.Code
		}

		_ = writeJSON(stdout, jsonError{
			Error:   "INTERNAL_ERROR",
			Message: err.Error(),
		})
		return clierr.ExitInternalError
	}

	return clierr.ExitOK
}

func writeJSON(w io.Writer, value any) error {
	encoder := json.NewEncoder(w)
	encoder.SetIndent("", "  ")
	return encoder.Encode(value)
}

func firstNonEmpty(values ...string) string {
	for _, value := range values {
		if value != "" {
			return value
		}
	}
	return ""
}
