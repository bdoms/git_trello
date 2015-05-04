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
The specifics of where to get each of those are described below.

### `api_key`

This is found on [the Trello website](https://trello.com/app-key)

### `board_name` and `board_id`

The name and ID for the board you want to access are found in the board URL, which is formatted like:

```
https://trello.com/b/[BOARD_ID]/[BOARD_NAME]
```

### `oauth_token`

Now that you have the required info you need to generate a token
by going to a URL in your browser that includes your `api_key` and `board_name`:

`https://trello.com/1/authorize?response_type=token&scope=read,write&expiration=never&key=[API_KEY]&name=[BOARD_NAME]`

### `list_id`

The `list_id` is optional. If provided, cards will be moved to this list after commenting.
It is surprisingly hard to find a list's ID via the Trello interface,
but easy to get via the API, so I built a helper function.
To get the ID, simply call the provided `trello.py` file from the command line with the following arguments:

```bash
python trello.py api_key oauth_token board_id list_name
```

Note that `list_name` is the case sensitive display name at the top of the list.


## Credits

Inspired in part by [a similar Ruby post-recieve hook](https://github.com/zmilojko/git-trello),
[a Python pre-push example](http://axialcorps.com/2014/06/03/preventing-errant-git-pushes-with-a-pre-push-hook/),
and [this pre-push sample](https://github.com/raven/git-prepush-recipes/blob/master/pre-push.sample).
