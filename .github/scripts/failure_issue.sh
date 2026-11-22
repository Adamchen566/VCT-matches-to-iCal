#!/usr/bin/env bash
# Open, update or close the GitHub issue that tracks failed calendar updates.
#
#   failure_issue.sh report    a run failed: open the issue, or comment on the open one
#   failure_issue.sh resolve   a run succeeded: close the open issue, if any
#
# Needs the gh CLI with GH_TOKEN, plus the GITHUB_* variables Actions provides.
set -euo pipefail

action="${1:?usage: failure_issue.sh report|resolve}"
label="auto-update-failure"
title="日历自动更新失败"
log_file="${UPDATE_LOG:-update.log}"
run_url="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"

open_issue_number() {
  gh issue list --state open --label "$label" --json number --jq '.[0].number // empty'
}

gh label create "$label" --color D93F0B --force \
  --description "定时更新失败时由工作流自动创建" >/dev/null

case "$action" in
  report)
    body="$(mktemp)"
    {
      echo "日历更新在 $(date -u '+%Y-%m-%d %H:%M UTC') 失败，订阅日历可能没有更新。"
      echo
      echo "- 运行记录：${run_url}"
      echo "- 触发方式：${GITHUB_EVENT_NAME:-unknown}"
      echo
      if [ -s "$log_file" ]; then
        echo "更新日志的最后 40 行："
        echo
        echo '~~~text'
        tail -n 40 "$log_file"
        echo '~~~'
      else
        echo "没有更新日志，失败发生在更新步骤之前，请查看运行记录。"
      fi
      echo
      echo "下一次运行成功后，这个 Issue 会自动关闭。"
    } > "$body"

    number="$(open_issue_number)"
    if [ -n "$number" ]; then
      gh issue comment "$number" --body-file "$body"
    else
      gh issue create --title "$title" --label "$label" --body-file "$body"
    fi
    ;;

  resolve)
    number="$(open_issue_number)"
    if [ -n "$number" ]; then
      gh issue close "$number" --comment "更新已恢复正常：${run_url}"
    else
      echo "没有未关闭的失败 Issue"
    fi
    ;;

  *)
    echo "unknown action: $action" >&2
    exit 2
    ;;
esac
