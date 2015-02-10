## Viviparidae

Viviparidae is a auto-commit tool for git.

Just run Viviparidae on your working directory. And Viviparidae make a temporary branch, and auto committing all changes in your working directory.

For all that, you can still use a original branches.


### How do it use

Just run Viviparidae on your working directory like next commands.
I recommend using background processing.

    cd /path/to/your/wroking/directory
    python /path/to/viviparidae.py >> /path/to/viviparidae.log~ &


### How do it work

Viviparidae monitoring your working directory, and find all changes include create and delete.

If found some change, first of all, Viviparidae staging all changes in your working branch.

And Viviparidae make new temporary branch - if it isn't a first commit of this branch, it just checkout to the branch and commit everything.

Finally it return to your working branch.

So, your all works is saved in Viviparidae branch and staged in your branch.

In addition, If you manually commit to your branch, Viviparidae remove all temporary commits. Because it's no need after the commit.


### REQUIREMENTS

Viviparidae needs the `GitPython` and `watchdog`.

* GitPython
* watchdog

You can try next command.

    pip install gitpython watchdog 
    

### LICENSE

MIT License.  See the LICENSE file.
