# コマンド集

## セットアップ
gh auth login
gh auth status
gh auth setup-git

## Pull Requests
gh pr create
gh pr create --title "Add feature" --body "Description"
gh pr create --base main --head feature-branch
gh pr create --draft
gh pr create --fill

gh pr list
gh pr list --author @me
gh pr view 123
gh pr view 123 --web
gh pr diff 123
gh pr status

gh pr checkout 123
gh pr review 123 --approve
gh pr review 123 --comment --body "Looks good!"
gh pr review 123 --request-changes --body "Please fix X"
gh pr merge 123
gh pr merge 123 --squash
gh pr merge 123 --rebase
gh pr merge 123 --merge
gh pr close 123
gh pr reopen 123
gh pr ready 123
gh pr update-branch 123

gh pr checks 123
gh pr checks 123 --watch

## Issues
gh issue create
gh issue create --title "Bug report" --body "Description"
gh issue create --title "Bug" --label bug,critical
gh issue create --title "Task" --assignee @me

gh issue list
gh issue list --assignee @me
gh issue list --label bug
gh issue view 456
gh issue view 456 --web

gh issue close 456
gh issue reopen 456
gh issue edit 456 --title "New title"
gh issue edit 456 --add-label bug
gh issue edit 456 --add-assignee @user
gh issue comment 456 --body "Update"
gh issue develop 456 --checkout

## Repository
gh repo view
gh repo view --web
gh repo clone owner/repo
gh repo fork owner/repo
gh repo list owner
gh repo create my-repo --public
gh repo create my-repo --private
gh repo sync owner/repo
gh repo set-default

## Search
gh search repos "machine learning" --language=python
gh search repos --stars=">1000" --topic=kubernetes
gh search issues "bug" --label=critical --state=open
gh search issues -- "memory leak -label:wontfix"
gh search prs --author=@me --state=open
gh search prs "refactor" --created=">2024-01-01"

## Labels
gh label list
gh label create "priority: high" --color FF0000 --description "High priority items"
gh label edit "bug" --color FFAA00 --description "Something isn't working"
gh label clone owner/source-repo

## Codespaces
gh codespace list
gh codespace create --repo owner/repo
gh codespace ssh
gh codespace code
gh codespace jupyter
gh codespace cp local-file.txt remote:~/path/
gh codespace cp remote:~/path/file.txt ./local-dir/
gh codespace logs

## Releases
gh release create v1.0.0
gh release create v1.0.0 --notes "Release notes"
gh release create v1.0.0 dist/*.tar.gz
gh release create v1.0.0 --draft
gh release create v1.0.0 --generate-notes
gh release list
gh release view v1.0.0
gh release download v1.0.0

## Gists
gh gist create file.txt
echo "content" | gh gist create -
gh gist list
gh gist view <gist-id>
gh gist edit <gist-id>

## Configuration
gh config set editor vim
gh config set git_protocol ssh
gh config list
gh config set browser firefox

## JSON 出力のフィールド確認
gh repo view --help | grep -A 50 "JSON FIELDS"
gh pr list --help | grep -A 50 "JSON FIELDS"

## JSON フィールド例
gh repo view owner/repo --json name,description,stargazerCount,forkCount,updatedAt,url,readme
