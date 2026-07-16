package cryptoids

import (
	"crypto/rand"
	"encoding/base32"
	"errors"
	"fmt"
	"io"
	"strings"
)

var ErrInvalidPrefix = errors.New("invalid opaque ID prefix")

type Generator struct {
	Random io.Reader
}

func (g Generator) NewID(prefix string) (string, error) {
	if len(prefix) < 2 || len(prefix) > 12 {
		return "", ErrInvalidPrefix
	}
	for _, value := range prefix {
		if (value < 'a' || value > 'z') && (value < '0' || value > '9') {
			return "", ErrInvalidPrefix
		}
	}
	random := g.Random
	if random == nil {
		random = rand.Reader
	}
	buffer := make([]byte, 20)
	if _, err := io.ReadFull(random, buffer); err != nil {
		return "", fmt.Errorf("read secure random bytes: %w", err)
	}
	encoded := base32.StdEncoding.WithPadding(base32.NoPadding).EncodeToString(buffer)
	return prefix + "_" + strings.ToLower(encoded), nil
}
