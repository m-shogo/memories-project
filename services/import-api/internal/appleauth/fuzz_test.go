package appleauth

import "testing"

func FuzzParseCompactTokenNeverPanics(f *testing.F) {
	f.Add("eyJhbGciOiJSUzI1NiIsImtpZCI6ImtleSJ9.eyJpc3MiOiJodHRwczovL2FwcGxlaWQuYXBwbGUuY29tIn0.c2lnbmF0dXJl")
	f.Add("..")
	f.Add("not-a-token")
	f.Add("")

	f.Fuzz(func(t *testing.T, token string) {
		if len(token) > MaxIdentityTokenBytes+1024 {
			t.Skip()
		}
		_, _, _, _, _ = parseCompactToken(token)
	})
}
