package genericcsv

import (
	"bytes"
	"testing"
)

func FuzzParserNeverPanicsOrExpandsLimits(f *testing.F) {
	f.Add([]byte("title,url\nA,https://example.com/a\n"))
	f.Add([]byte("title,note\nA,=HYPERLINK(\"https://example.com\")\n"))
	f.Add([]byte("Title, title \nA,B\n"))
	f.Add([]byte{'t', 'i', 't', 'l', 'e', '\n', 0xff, '\n'})

	f.Fuzz(func(t *testing.T, data []byte) {
		if len(data) > 64*1024 {
			t.Skip()
		}
		emitted := 0
		_, _ = (Parser{}).Parse(bytes.NewReader(data), Options{
			TitleColumn:   "title",
			MaxInputBytes: 64 * 1024,
			MaxRows:       100,
			MaxColumns:    32,
			MaxCellBytes:  4096,
		}, func(result Result) error {
			emitted++
			if emitted > 100 {
				t.Fatalf("parser emitted more rows than the configured limit: %d", emitted)
			}
			if result.Accepted && len(result.Candidate.Fingerprint) != 64 {
				t.Fatalf("accepted candidate has invalid fingerprint length: %d", len(result.Candidate.Fingerprint))
			}
			return nil
		})
	})
}
