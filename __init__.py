import datetime
import re
import sys

from lib.trello import Trello
from lib import git

REPO = re.compile(':(.+)\.git')
CARD = re.compile('#([0-9]+)')


class GitTrelloHook(object):

    def __init__(self, api_key='', oauth_token='', board_id='', list_id='',
        branch='', release_branch='', release_remote='',
        release_name='%Y-%m-%d Release', verbose=False, strict=False,
        force_override=False, exhaustive=False):

        # NOTE that although required these are not positional arguments so that someone can glance at the hook file
        #      and know exactly what each thing is because it's a named argument
        if not api_key: sys.exit('Trello: api_key is required - aborting.')
        if not oauth_token: sys.exit('Trello: oauth_token is required - aborting.')
        if not board_id: sys.exit('Trello: board_id is required - aborting.')

        self.client = Trello(api_key, oauth_token, board_id)
        self.list_id = list_id
        self.branch = branch
        self.release_branch = release_branch
        self.release_remote = release_remote
        self.release_name = release_name
        self.verbose = verbose
        self.strict = strict
        self.force_override = force_override
        self.exhaustive = exhaustive
        self.base_url = ''

        # command line arguments;
        #hook_path = sys.arg[0]
        #remote_name = sys.argv[1]
        remote_url = sys.argv[2]

        # github is the only supported remote for adding a link to the commit
        # but this would be trivial to extend to others
        if remote_url.startswith('git@github.com:'):
            # git@github.com:user/repo.git
            result = REPO.search(remote_url)
            user_repo = result.group(1)
            self.base_url = 'https://github.com/' + user_repo + '/commit/'

    def pre_push(self):

        current_branch = git.currentBranch()
        if self.branch and current_branch != self.branch:
            if self.verbose:
                print 'Trello: pushing unspecified branch skips modifying cards'
            return

        # if forcing assume that all the commits already exist
        # but probably now have new SHAs we can't detect so we don't want to update anything
        forced = git.pushForced()
        if forced and not self.force_override:
            if self.verbose:
                print 'Trello: force pushing skips modifying cards'
            return

        # stuff comes in on stdin, see http://git-scm.com/docs/githooks#_pre-push
        # of the form: <local ref> SP <local sha1> SP <remote ref> SP <remote sha1> LF
        # example: refs/heads/master 67890 refs/heads/foreign 12345
        # also note "If the foreign ref does not yet exist the <remote SHA-1> will be 0" (in fact 40 zeros for the full sha)
        z40 = '0' * 40

        # list of card ID's that had old commits removed when force pushing
        old_commits_removed = []

        # list of cards that were actually modified
        cards = []

        for line in sys.stdin:
            local_ref, local_sha, remote_ref, remote_sha = line.replace('\n', '').split(' ')

            if local_sha == z40 or local_sha == remote_sha:
                # deleting branch or up to date so exit early
                return

            if remote_sha == z40:
                # new branch so look at all commits
                commit_range = local_sha
            else:
                commit_range = remote_sha + '..' + local_sha
            
            # see http://git-scm.com/book/ch2-3.html for formatting details
            all_commits = commits = git.commitDetails('%H %h', commit_range)

            # if there's a specified branch then we don't care if the commit was pushed somewhere else
            if not self.branch:
                commits = []
                for i, commit in enumerate(all_commits):
                    long_sha, short_sha = commit.split(' ')

                    # list remote branches that contain this commit
                    branches = git.branchesWithCommit(long_sha, remote=True)
                    if branches:
                        if self.exhaustive:
                            if self.verbose:
                                print 'Trello: ' + short_sha + ' has already been pushed on another branch'
                            continue
                        else:
                            if self.verbose:
                                print 'Trello: ' + short_sha + ' marks beginning of pushed commits, stopping there'
                            break
                    else:
                        commits.append(commit)

            # need to reverse the input so that the oldest commits are handled first
            commits.reverse()
            
            for commit in commits:
                long_sha, short_sha = commit.split(' ')

                body = git.commitBody(long_sha)

                card_id = ''
                result = CARD.search(body)
                if result:
                    card_id = result.group(1)
                if not card_id:
                    warning = 'Trello: ' + short_sha + ' no card number'
                    if self.strict:
                        return sys.exit(warning)
                    if self.verbose:
                        print warning
                    continue

                # figure out the full card id
                card = self.client.getCard(card_id)
                if not card:
                    warning = 'Trello: ' + short_sha + ' cannot find card #' + card_id
                    if self.strict:
                        return sys.exit(warning)
                    if self.verbose:
                        print warning
                    continue

                # remove previous commit messages on card if force pushed
                if forced and self.force_override and card_id not in old_commits_removed:
                    comments = self.client.getComments(card)
                    commit_comments = []
                    for comment in comments:
                        text = comment['data']['text']
                        if text.startswith(self.base_url) and '[#' + card_id + ']' in text:
                            # we don't want to remove comments that contain valid commits
                            # they won't get re-added as git is smart enough to not include those commits here
                            # so parse out the sha and check to see if it exists anywhere before deleting this comment
                            old_sha = text.split('\n')[0].rsplit('/', 1)[1]
                            local_branches = git.branchesWithCommit(old_sha)
                            if not local_branches:
                                # even if it doesn't exist locally it's possible someone else added it on another branch
                                remote_branches = git.branchesWithCommit(old_sha, remote=True)
                                if not remote_branches:
                                    commit_comments.append(comment)
                                elif len(remote_branches) == 1:
                                    # if the only remote branch is this one then the sha will disappear as soon as we push
                                    remotes = git.remotes()
                                    for remote in remotes:
                                        if remote + '/' + current_branch in remote_branches:
                                            commit_comments.append(comment)
                                            break
                    if commit_comments:
                        if self.verbose:
                            count = str(len(commit_comments))
                            print 'Trello: ' + short_sha + ' deleting ' + count + ' previous comment(s) on card #' + card_id
                        self.client.deleteComments(commit_comments)
                    old_commits_removed.append(card_id)

                # comment on the card
                if self.verbose:
                    print 'Trello: ' + short_sha + ' commenting on card #' + card_id
                comment = ''
                if self.base_url:
                    comment += self.base_url + long_sha + '\n\n'
                comment += body                
                self.client.addComment(card, comment)

                # move the card
                if self.list_id and card['idList'] != self.list_id:
                    if self.verbose:
                        print 'Trello: ' + short_sha + ' moving card #' + card_id + ' to list ' + self.list_id
                    self.client.moveCard(card, self.list_id, pos='bottom')

                cards.append(card)

        if self.release_branch and current_branch == self.release_branch:
            push_remote = git.pushRemote()
            if not self.release_remote or push_remote == self.release_remote:
                if self.verbose:
                    print 'Trello: moving cards to new release list'
                now = datetime.datetime.now()
                release_name = now.strftime(self.release_name)
                release_list = self.client.createList(release_name, self.list_id)
                cards = self.client.moveCards(self.list_id, release_list['id'])

        return cards
