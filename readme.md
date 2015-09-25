Copyright &copy; 2015, [Brendan Doms](http://www.bdoms.com/)  
Licensed under the [MIT license](http://www.opensource.org/licenses/MIT)  


# Git Trello

A pre-push hook to automatically add git commit messages to Trello cards.


## The Situation

I love GitHub and I love Trello. Maybe you do too.
Maybe you've noticed that they don't have very good integration out of the box.
GitHub *does* have a service hook you can check out:

`https://github.com/[USER]/[REPO]/settings/hooks/new?service=trello`

You'll notice that - bizarrely - its main function is to add a new card per commit.
I'd be very interested in what the use case behind that decision was.
What makes way more sense to me is to add a *comment* for each commit.

To do that, there are some pre-existing solutions out there.
But most of them use hooks like `post-receive` that run on the remote.
Since GitHub is my remote and I therefore can't customize its hooks, those won't work for me.

Luckily, git added a `pre-push` hook,
so your local machine can do all the work without having to control the remote you're pushing to.
Add to that Trello's easy to use API and that's how this came about.


## Setup

Copy the `pre-push` file to your repo's `.git/hooks/pre-push`
or integrate it with an existing file if you already have one.
Make sure that the import line will work correctly for where you put this project.
Then replace all of the arguments in the hook with your own values.
The specifics of how to get the required values are in the readme of
[the Trello submodule](https://github.com/bdoms/trello).

### Optional Arguments

#### `list_id`

If provided, cards will be moved to this list after commenting.

#### `branch`

By default all branches are considered valid,
but if you specify one then only pushes for that branch are inspected.
If you use a merging workflow then this is not necessary as commit hashes will remain consistent across branches.
However, if you rebase then new hashes are generated and thus links to commits that no longer exist will be broken.
Using this means you *must* push a commit on the specified branch for it to be modified in Trello,
so it does not work very well with a process that uses things like pull requests.
See `force_override` below for an alternate approach.

#### `verbose`

By default printing is suppressed.
Set `verbose` to `True` to get more information about all the actions being taken.

#### `strict`

By default if a commit does not contain a card number or that number can't be found on Trello no action is taken.
Set `strict` to `True` to make the push operation abort instead.
This can useful for enforcing strict standards like "all commits must reference a card"
or for allowing authors to ammend commits if they entered in an erroneous card number that doesn't exist.

#### `force_override`

By default force pushes are ignored. By setting `force_override` to `True` you can allow force pushes to modify cards.
In this case old comments referencing commits that no longer exist will be deleted,
and new comments will be made for the new hashes. This ensures that the links in Trello will remain up to date,
but it makes the most requests and will take the longest amount of time.

## Credits

Inspired in part by [a similar Ruby post-recieve hook](https://github.com/zmilojko/git-trello),
[a Python pre-push example](http://axialcorps.com/2014/06/03/preventing-errant-git-pushes-with-a-pre-push-hook/),
and [this pre-push sample](https://github.com/raven/git-prepush-recipes/blob/master/pre-push.sample).
