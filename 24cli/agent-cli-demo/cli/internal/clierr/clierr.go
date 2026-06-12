package clierr

type Error struct {
	Code    int
	Name    string
	Message string
}

func (e *Error) Error() string {
	return e.Message
}

func New(code int, name, message string) *Error {
	return &Error{
		Code:    code,
		Name:    name,
		Message: message,
	}
}

const (
	ExitOK               = 0
	ExitAuthRequired     = 10
	ExitTokenExpired     = 11
	ExitPermissionDenied = 12
	ExitInvalidArgument  = 20
	ExitNetworkError     = 30
	ExitInternalError    = 50
)
