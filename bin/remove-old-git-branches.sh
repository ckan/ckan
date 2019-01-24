#!/usr/bin/env bash

# Change this variable if you are using another name for ckan/ckan's remote
REMOTE=origin
PR_ENDPOINT=https://api.github.com/repos/ckan/ckan/pulls

prepare_branches() {
  echo List existing branches
  # awk filters out `master`, `release-something`, `dev-something` and `MAJOR.MINOR-something` branches
  custom_branches=$(git fetch $REMOTE && git branch -r --list $REMOTE/* | awk '{ if ($2 !~ /^[0-9]\.[0-9]|^release|^dev-|^master$|HEAD/) print $2}' FS=/)

  echo Calculate total amount of active PRs
  # github adds Link header, that contains reference to last page with results. And that helps us to define total number of pages
  last_page=$(curl -s -I $PR_ENDPOINT | grep '^Link' | sed -E 's/.*page=([[:digit:]]+).*rel="last".*/\1/')

  echo Compute branches that are in use by active PRs
  for ((i=1; i<=$last_page; i++))
  do
    # Take JSON, get name of branch with feature, leave only those ones, that starts with `ckan:`. I think, that jq is much more nice way to process json, but i'm not sure, that every one has it. But if you do,
    # you can replace python's section with something like `| jq '.[] | .head.label' -r |`
    next_portion=$(curl -s "$PR_ENDPOINT?page=$i" | python -c 'import json, sys; raw=sys.stdin.read(); labels=[str(item["head"]["label"]) for item in json.loads(raw)]; print("\n".join(labels))' | grep '^ckan' | sed 's/^ckan://')
    used_branches="$used_branches\n$next_portion"
    echo [$i of $last_page parts processed]
  done;

  echo Compute list of branches that can be safetely removed
  tmp_file=$(mktemp)
  diff <(echo -e "$used_branches" | sort) <(echo -e "$custom_branches" | sort) --unchanged-line-format="" >> $tmp_file

  echo
  echo List of all branches that can be removed stored into $tmp_file. Review it\'s content and run \'$0 --apply $tmp_file\'.
  echo NOTE. This command requires write access to CKAN repository and will actually remove all branches that are listed in $tmp_file.
}

if [[ $# -gt 0 ]];
then
  case "$1" in
    -h|--help)
      echo Compute/remove unused branches
      echo Usage: $0 [--apply FILE_WITH_BRANCHES]
      ;;
    --apply)
      shift
      if [[ -f $1 ]]
      then
        while read branch
        do
          git push $REMOTE --delete $branch
        done < $1
      else
        echo File does not exist
      fi
      shift
      ;;
    *)
      echo Check usage with: $0 --help
      ;;
  esac
else
  prepare_branches
fi
