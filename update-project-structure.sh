#!/bin/bash

# Configuration
OUTPUT_FILE="PROJECT_STRUCTURE.md"
PROJECT_ROOT="."
MAX_DEPTH=3  # Limit the maximum depth to prevent overly nested structures
# Directories/files to exclude (space-separated patterns)
EXCLUDES=".git node_modules .DS_Store .idea .vscode build dist tmp cache coverage logs .env .env.* *.log package-lock.json yarn.lock .gitignore .npmignore .eslintcache .nyc_output .editorconfig .prettierrc __pycache__ flask_session myenv .venv .vercel"

# Build exclude parameters for find command
EXCLUDE_PARAMS=""
for pattern in $EXCLUDES; do
  EXCLUDE_PARAMS="$EXCLUDE_PARAMS -not -path '*/$pattern/*' -not -path '*/$pattern'"
done

# Create header with timestamp
echo "# Project Structure" > $OUTPUT_FILE
echo "" >> $OUTPUT_FILE
echo "Last updated: $(date)" >> $OUTPUT_FILE
echo "" >> $OUTPUT_FILE

# Add tree structure
echo "## Directory Tree" >> $OUTPUT_FILE
echo "" >> $OUTPUT_FILE
echo '```' >> $OUTPUT_FILE

# Additional file patterns to exclude (file extensions that are usually not relevant)
FILE_EXCLUDE_PATTERN=".*\.\(jpg\|jpeg\|png\|gif\|svg\|ico\|woff\|woff2\|ttf\|eot\|otf\|mp4\|webm\|ogg\|mp3\|wav\|flac\|min\.js\|min\.css\|chunk\.js\|bundle\.js\|pyc\|cpython-.*\)$"

# Specifically include only the important files and directories
find $PROJECT_ROOT -maxdepth 1 -type d \( -name "api" -o -name "prompts" -o -name "static" -o -name "templates" -o -name "utils" \) -o -maxdepth 1 -type f \( -name "*.py" -o -name "*.js" -o -name "*.json" -o -name "*.html" -o -name "*.md" -o -name "requirements.txt" \) | grep -v "$FILE_EXCLUDE_PATTERN" | sort | while read line; do
  # Count the depth by counting slashes
  depth=$(echo "$line" | tr -cd '/' | wc -c)
  
  # Indent based on depth
  indent=$(printf "%$((depth * 2))s" "")
  
  # Show just the base name
  basename=$(basename "$line")
  
  # Add directory indicator
  if [ -d "$line" ]; then
    echo "$indent$basename/" >> $OUTPUT_FILE
    
    # For directories, find their contents up to 1 level deep
    find "$line" -maxdepth 1 \( -type f -o -type d \) -not -path "*/\.*" | grep -v "__pycache__" | sort | while read subline; do
      # Skip if it's the same as the directory we're processing
      if [ "$subline" = "$line" ]; then
        continue
      fi
      
      # Count the depth for subdirectory/file
      subdepth=$((depth + 1))
      
      # Indent based on subdepth
      subindent=$(printf "%$((subdepth * 2))s" "")
      
      # Show just the base name of the subdirectory/file
      subbasename=$(basename "$subline")
      
      # Add directory indicator
      if [ -d "$subline" ]; then
        echo "$subindent$subbasename/" >> $OUTPUT_FILE
      else
        echo "$subindent$subbasename" >> $OUTPUT_FILE
      fi
    done
  else
    echo "$indent$basename" >> $OUTPUT_FILE
  fi
done

echo '```' >> $OUTPUT_FILE

echo "Project structure has been updated in $OUTPUT_FILE"