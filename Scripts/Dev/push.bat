cd ../../

@echo off

:: Ask for commit message
set /p commitMessage="Enter commit message: "

git add .


::Commit changes
git commit -m "%commitMessage%"

::Confirm remote repository
git remote -v

::Push changes to remote repository
git push origin main

cmd /k