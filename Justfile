release tag:
  #!/usr/bin/env bash
  set -euo pipefail

  TAG_COMMIT=$(git rev-parse {{tag}})
  echo "performing release for {{tag}} @ commit $TAG_COMMIT"

  SDIST_ID=$(gh run list \
     --workflow sdist.yml --json databaseId,headSha --status completed | \
     jq --raw-output ".[] | select(.headSha==\"$TAG_COMMIT\") | .databaseId" | head -n 1)
  if [ -z "$SDIST_ID" ]; then
    echo "could not find GitHub Actions run for sdist artifact"
    exit 1
  fi

  WHEEL_ID=$(gh run list \
    --workflow wheel.yml --json databaseId,headSha --status completed | \
    jq --raw-output ".[] | select(.headSha==\"$TAG_COMMIT\") | .databaseId" | head -n 1)
  if [ -z "$WHEEL_ID" ]; then
    echo "could not find GitHub Actions run for wheels artifacts"
    exit 1
  fi

  rm -rf dist/{{tag}} && mkdir -p dist/{{tag}}/assets dist/{{tag}}/final
  gh run download --dir=dist/{{tag}}/assets $SDIST_ID
  gh run download --dir=dist/{{tag}}/assets $WHEEL_ID

  find dist/{{tag}}/assets -name '*.tar.gz' -exec cp {} dist/{{tag}}/final/ ';'
  find dist/{{tag}}/assets -name '*.whl' -exec cp {} dist/{{tag}}/final/ ';'

  echo "creating GitHub release {{tag}}"
  gh release create \
    --prerelease \
    --target=$TAG_COMMIT \
    --title={{tag}} \
    --discussion-category=general \
    --notes-from-tag \
    {{tag}}
  gh release upload --clobber {{tag}} dist/{{tag}}/final/*

  echo "uploading to PyPI"
  token=$(uv run --no-project -w keyring keyring get pypi token)

  # Upload the source distribution first because it can trigger additional
  # validation that can result in an incomplete release being published.
  UV_PUBLISH_TOKEN=$token uv publish dist/{{tag}}/final/*.tar.gz
  UV_PUBLISH_TOKEN=$token uv publish dist/{{tag}}/final/*.whl
