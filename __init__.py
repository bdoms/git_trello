import os
import re
import subprocess
import sys

from lib.trello import Trello

REPO = re.compile(':(.+)\.git')
CARD = re.compile('#([0-9]+)')


class GitTrelloHook(object):

    def __init__(self, api_key='', oauth_token='', board_id='', list_id='', verbose=False, strict=False):
        # NOTE that although required these are not positional arguments so that someone can glance at the hook file
        #      and know exactly what each thing is because it's a named argument
        if not api_key: sys.exit('Trello: api_key is required - aborting.')
        if not oauth_token: sys.exit('Trello: oauth_token is required - aborting.')
        if not board_id: sys.exit('Trello: board_id is required - aborting.')

        self.client = Trello(api_key, oauth_token, board_id)
        self.list_id = list_id
        self.verbose = verbose
        self.strict = strict
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

        pid = os.getppid()
        push_command = subprocess.check_output(['ps', '-ocommand=', '-p', str(pid)])
        forcing = ('--force' in push_command or '-f' in push_command)

        # if forcing assume that all the commits already exist
        # but probably now have new SHAs we can't detect so we don't want to update anything
        if forcing:
            if self.verbose:
                print 'Trello: force pushing skips modifying cards'
            return

        # stuff comes in on stdin, see http://git-scm.com/docs/githooks#_pre-push
        # of the form: <local ref> SP <local sha1> SP <remote ref> SP <remote sha1> LF
        # example: refs/heads/master 67890 refs/heads/foreign 12345
        # also note "If the foreign ref does not yet exist the <remote SHA-1> will be 0" (in fact 40 zeros for the full sha)
        z40 = '0' * 40

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
            output = subprocess.check_output(['git', 'log', '--pretty=format:"%H %h"', commit_range])
            commits = output.replace('"', '').split('\n')
            
            for commit in commits:
                long_sha, short_sha = commit.split(' ')

                # list remote branches that contain this commit
                branches = subprocess.check_output(['git', 'branch', '-r', '--contains', long_sha])
                if branches:
                    if self.verbose:
                        print 'Trello: ' + short_sha + ' has already been pushed on another branch'
                    continue

                body = subprocess.check_output(['git', 'log', '--pretty=format:"%B"', '-n', '1', long_sha])
                body = body[1:-1].strip() # body is surrounded by quotes (e.g. '"commit message"')

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
                    self.client.moveCard(card, self.list_id)
