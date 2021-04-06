# Copy of https://gist.github.com/antonio/4586456
# With a modification to collect all the branch names so we can make one git request
# Set DRY_RUN=1 to get an echo of the command

DRY_RUN=1

# Format that works with `git log --since`, e.g. 2018-01-01
date=$1

branches=

for branch in $(git branch -a | sed 's/^\s*//' | sed 's/^remotes\///' | grep -v 'cioos$\|master$'); do
  if [[ "$(git log $branch --since $date | wc -l)" -eq 0 ]]; then
    if [[ "$branch" =~ "origin/" ]]; then
      if [[ -z $branches ]]; then
        branches=$(echo "$branch" | sed 's/^origin\///')
      else
        branches="$branches "$(echo "$branch" | sed 's/^origin\///')
      fi
    fi
  fi
done

if [[ ! -z $branches ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo git branch -D $branches
    echo git push --delete origin $branches
  else
    git branch -D $branches
    git push --delete origin $branches

    # clean up locally
    git remote prune origin
  fi
fi
