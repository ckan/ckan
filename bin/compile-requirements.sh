##!/usr/bin/env sh

out=requirements.txt
versions=

while getopts :hyv:o: opt; do
  case $opt in
    y)
      NO_CONFIRM=1
      ;;
    o)
      out=$OPTARG
      ;;
    v)
      versions="$versions $OPTARG"
      ;;
    h)
      echo "Compile CKAN requirements"
      printf "\t-h\t\tPrint this message\n"
      printf "\t-y\t\tRun without confirmation\n"
      printf "\t-o {FILE}\tOutput file for requirements(default: requirements.txt)\n"
      printf "\t-v {VERSION}\tPython versions that are used while building requirements(multiple)\n"
      exit 0
      ;;
    *)
      ;;
  esac
done

if [ -z "$versions" ]; then
  echo "No versions(-v) specified"
  exit 1
fi



if [ -z $NO_CONFIRM ]; then
  echo "Build requirements for $versions?[y/n]"
  read -r response
  if [ "$response" != "y" ]; then
    exit 0
  fi
fi

# pip install wheel pip-tools

truncate "$out" --size 0

last=$(echo "$versions" | tr " " "\n" | sort -V | tail -n1)

for version in $versions; do
  if [ "$version" = "$last" ]; then
    op=">="
  else
    op="=="
  fi

  echo "Switch python version to $version"
  pyenv local "$version";

  venv="/tmp/req-venv/$version"
  echo "Create virtual environment and install pip-tools"
  python -m venv "$venv"
  "$venv/bin/pip" install wheel pip-tools

  echo "Compile requirements for $version"
  "$venv/bin/pip-compile" requirements.in -o current.txt;
  sed -n -E "/^\w/s/(\s+.*)?$/; python_version $op '${version%.*}'/p" < current.txt >> "$out";
  rm -f current.txt;
done

sort -o "$out" "$out"
