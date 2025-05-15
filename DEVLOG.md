
2025-05-14: 
- working on adding io.StringIO as the way to pass around print
output so it can be passed to shell command
- successfully added stringIO to all the print statements, so the print
output goes to the stringIO buffer instead of stdout. now I can return the string
 buffer (and later use it for shell input)
