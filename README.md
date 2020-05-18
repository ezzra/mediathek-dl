# mediathek-dl

Mit diesem python tool kannst du mehrere Medien auf einmal aus den Mediatheken (Arte, ARD, 3SAT....) herunterladen. 
Damit ist es eine Alternative auf der Kommandozeile zur Website mediathekviewweb.de und bringt schließt damit ein paar Lücken:

- läuft auf der Komandozeile, kann also auch direkt auf einem Web- oder Fileserver etc. eingesetzt werden.
- kann viele Medien auf einmal runterladen, so können beispielsweise Mehrteiler und Serien bequem heruntergeladen werden.
- speichert die Dateien unter ihrem korrekten Titelnamen ab, für Mehrteiler/Serien auch in einem Format das z.B. von Emby gelesen werden kann.
- kann die Downloadbefehle auch über `ssh curl/wget` ausführen und muss damit nichtmal auf dem server selbst installiert werden
- unbeliebige Ergebnisse können über frei wählbare Stichworte auch ausgeblendet werden, z.B. die "Hörfassung"

_**Derzeitiges Hauptproblem**: Die Daten werden derzeit über den MediathekViewWeb Feed ausgelesen, leider wird dort nur der Download 
zur höchsten Qualität angegben._

### Installation

**1.a)** Clone this repository\
`git clone https://github.com/ezzra/mediathek-dl`

**1.b)** OR download the zip and unpack it\
[https://github.com/ezzra/mediathek-dl/archive/master.zip](https://github.com/ezzra/mediathek-dl/archive/master.zip)

**2.a)** open the folder and create an environment using `pipenv` (if you have installed)\
`pipenv install`

then run `mediathek-dl` from your command line using this environment\
`pipenv run python mediathek-dl -h`

**2.b)** OR open the folder and install the requirements using `pip`\
`pip3 install -r requirements.txt`

then run `mediathek-dl` from your command line\
`python3 mediathek-dl -h`

### Usage

Easiest way to make `mediathek-dl` work is just\
`python3 mediathek-dl 'The War'`

This will download ALL the media files that are found on [mediathekviewweb.de](https://mediathekviewweb.de) with this searchstring. Normally that would be too much, check in the Repo how to [improve your searchstring](https://github.com/mediathekview/mediathekviewweb#erweiterte-suche). For our example we could use:

`python3 mediathek-dl '!arte The War Geschichte' -t`

This will show you all 14 parts of the documentary miniseries "[The War](https://en.wikipedia.org/wiki/The_War_(miniseries))" and nothing else. The `-t` or `--test` here lets you check first for your results. You can check it also more comfy using the search on *mediathekviewweb.de*.

However, this command will start downloading the miniseries\
`python3 mediathek-dl '!arte The War Geschichte'`\

and it will create a folder structure like\
`The War/Season 01/The War - s14e01 - Ein notwendiger Krieg.mp4`

Checkout the help page for more functionality (reducing the result by negative searchstring, various output formats, ...)

```
positional arguments:
  search_string         the search string for the medias you want to download
  target_folder         folder where the media will be stored

optional arguments:
  -h, --help            show this help message and exit
  -o {save,wget,ssh,test,curl}, --output {save,wget,ssh,test,curl}
                        output format
  --ssh SSH             if output is ssh, you need to give your user@localhost
                        server address
  -b, --blindness       show videos with "Hörfassung" in title (disabled by
                        default)
  -n NOT_SEARCH, --not_search NOT_SEARCH
                        words you want to exclude from result, for example
                        "Hörfassung" (separate multiple by commata)
  -v, --verbose         show verbose output
  -t, --test            just show list of titles
  ```
