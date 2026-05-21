#!/bin/bash

# WARNING: This script prepares the files for a destructive git rewrite.
# RUN THIS LOCALLY. DO NOT RUN THIS IF YOU DON'T UNDERSTAND THE RISKS.

REPO_DIR=$(pwd)
MAILMAP="$REPO_DIR/mailmap.txt"

echo "Creating mailmap.txt to remap other authors to 'elkarouh <elkarouh@gmail.com>'"

# Mapping based on typical contributor names found in history
cat <<EOF > "$MAILMAP"
claude <claude@example.com> elkarouh <elkarouh@gmail.com>
qwencoder <qwencoder@example.com> elkarouh <elkarouh@gmail.com>
michele-sciabarra <michele@example.com> elkarouh <elkarouh@gmail.com>
Hassan El Karouni <elkarouh@gmail.com> elkarouh <elkarouh@gmail.com>
EOF

echo "mailmap.txt created at $MAILMAP"
echo "-----------------------------------------------------------------"
echo "NEXT STEPS:"
echo "1. Back up your repository: git clone --mirror <url> backup-repo"
echo "2. Install git-filter-repo: pip install git-filter-repo"
echo "3. Run the rewrite: git filter-repo --mailmap mailmap.txt"
echo "4. Force push your changes: git push --force --all"
echo "-----------------------------------------------------------------"
