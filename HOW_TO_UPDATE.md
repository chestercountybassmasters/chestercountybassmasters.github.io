# How to change the website

You do not need to know any code. The things that change often live in six
small files in the `content` folder, and the photos live in the `photos` folder.

| To change… | Open this file |
|---|---|
| the sponsor list | `content/sponsors.md` |
| a photo, or the words under one | `content/photo-captions.md` |
| where and when we meet, the next meeting date | `content/meeting.md` |
| the officers | `content/officers.md` |
| a member's photo, boat or message board name in the gallery | `content/members.md` |
| the club schedule, the Opens dates | `content/schedule.md` |

Each file starts with a few lines saying how it works. Follow the pattern of the
lines already there.

## Changing words (on the GitHub website)

1. Sign in to GitHub and open the club's website repository,
   `chestercountybassmasters/chestercountybassmasters.github.io`.
2. Click the `content` folder, then the file you want.
3. Click the pencil at the top right of the file.
4. Change the words. Leave the punctuation that starts or ends a line (a dash,
   a colon, a bar `|`) as it is.
5. Click the green **Commit changes** button, write a few words saying what you
   changed ("Add Smith Marine to sponsors"), and click **Commit changes** again.

## Changing a photo

1. Open the `photos` folder, click **Add file**, then **Upload files**, and drop
   your picture in. Give it a short plain name first, with no spaces, such as
   `open-may-2027.jpg`. A picture about 1600 pixels wide is plenty.
2. Commit, as above.
3. Open `content/photo-captions.md`, find the place the photo goes (each one is
   described in plain words), and put your file name after `photo:`. Change the
   `shows:` line to say what is in the picture, and the `caption:` if there is one.
4. Commit.

## Then what?

Nothing. The site rebuilds itself. A few minutes after you commit, your change is
on the website; reload the page to see it.

Before it goes live, the site is checked. If a check fails (a photo name that does
not match a file in the `photos` folder is the usual cause), **nothing changes on
the website**: it stays as it was. GitHub sends an e-mail to whoever made the
change saying the run failed. Fix the line and commit again, or tell Steve.

To see how a change is doing, click the **Actions** tab at the top of the
repository: a yellow dot is still working, a green tick is live, a red cross
failed. Every change is kept and can be undone.

## Please leave alone

The `data` folder holds the tournament results, and the `templates`, `tools` and
`.github` folders are how the site is built: please ask Steve before changing
anything there. (The finished pages are not in the repository at all. GitHub
builds them each time from the files that are.) Words in [square brackets] on the site mark things we have not filled in
yet; replace the whole bracket, brackets included, when you have the real words.
