#!/usr/bin/env bash
set -euo pipefail
racine="$(cd "$(dirname "$0")/../.." && pwd)"
temporaire="$(mktemp -d)"
trap 'rm -rf -- "$temporaire"' EXIT
cc -std=c11 -Wall -Wextra -Werror -DJOURNAL_USB_PRESENT=1 \
  -I "$racine/main" -I "$racine/tests/usb/stubs" \
  "$racine/main/journal-usb.c" "$racine/tests/usb/test_usb.c" \
  -o "$temporaire/test-usb"
"$temporaire/test-usb"
cc -std=c11 -Wall -Wextra -Werror -DJOURNAL_USB_PRESENT=1 -DJOURNAL_MTLS_PRESENT=0 \
  -I "$racine/main" -I "$racine/tests/usb/stubs" \
  "$racine/tests/usb/test_file_usb.c" -o "$temporaire/test-file-usb"
"$temporaire/test-file-usb"
