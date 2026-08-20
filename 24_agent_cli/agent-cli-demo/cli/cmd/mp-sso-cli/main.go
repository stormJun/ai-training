package main

import (
	"context"
	"os"

	"agent-cli-demo/cli/internal/command"
)

func main() {
	os.Exit(command.ExecuteSSO(context.Background(), os.Args[1:], os.Stdout, os.Stderr))
}
