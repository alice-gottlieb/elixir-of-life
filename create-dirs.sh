while IFS= read -r name; do
  dir=$(echo "$name" | tr '[:upper:] /' '[:lower:]--')
  mkdir -p "$dir"
  echo '{"cells":[],"metadata":{},"nbformat":4,"nbformat_minor":5}' > "$dir/$dir.ipynb"
done < elixir-list.md
