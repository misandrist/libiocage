#!/bin/sh
# Run pep8 on all .py files in all subfolders

tmpafter=$(mktemp)
find ./libiocage/ -name \*.py -exec flake8 --ignore=E203,W391 {} + | grep -v "./libiocage/__init__.py" > ${tmpafter}
num_errors_after=`cat ${tmpafter} | wc -l`
echo "Current Error Count: ${num_errors_after}"
echo "Current Errors:"
cat "${tmpafter}"

# Get new tags from remote
git fetch --tags --quiet
# Get latest tag name
last_release=$(git describe --tags `git rev-list --tags --max-count=1`)

echo "Comparing with last stable release: ${last_release}"
git checkout ${last_release}

tmpbefore=$(mktemp)
find ./libiocage/ -name \*.py -exec flake8 --ignore=E203,W391 {} + | grep -v "./libiocage/__init__.py" > ${tmpbefore}
num_errors_before=`cat ${tmpbefore} | wc -l`
echo "${last_release}'s Error Count: ${num_errors_before}"

# The number may be lower then the last release, but that doesn't tell them that they're not higher than they should be.
num_errors_adjusted=$((num_errors_before-num_errors_after))

if [ ${num_errors_adjusted} != 0 ] && [ ${num_errors_adjusted} != ${num_errors_before} ]; then
	echo "New Flake8 errors were introduced:"
	diff -u ${tmpbefore} ${tmpafter}
	exit 1
fi
