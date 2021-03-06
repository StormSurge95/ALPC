# AdventureLand Python Client
This is meant to be a python client for the game [Adventure Land - The Code MMORPG](https://adventure.land). It's heavily inspired by and based on earthiverse's typescript-based [ALClient](https://github.com/earthiverse/ALClient).

Currently a major work in progress; but the current state is available through [pip](https://pypi.org/project/pip/) for simple installation and use.

## Requirements
This package currently requires `aiohttp`, `aiosignal`, `async-timeout`, `attrs`, `bidict`, `charset-normalizer`, `frozenlist`, `idna`, `igraph`, `multidict`, `python-engineio`, `setuptools`, `texttables`, `ujson`, and `yarl`. (Technially only some of these are dependencies of ALPC; others are dependencies of various dependencies).

**All** of these requirements are installable through pip, and their individual installations are also taken care of through the install of ALPC.

## Installation
The PyPI page can be found [here](https://pypi.org/project/ALPC/). In order to install, simply use pip like so:
<details><summary>Unix/Linux</summary>

  ```
  python3 -m pip install --upgrade ALPC
  ```

</details>
<details><summary>Windows</summary>
  
  ```
  py -m pip install --upgrade ALPC
  ```
  
</details>

* *Note: This package was developed with Python 3.10.4; therefore, I cannot guarantee that it will work with anything below that. In fact, due to current bugs, I cannot even guarantee that it will work perfectly **with** that.*

## Usage
* First: be sure to install the package from PyPI using pip.
* Second: create a `credentials.json` file like so (the 'mongo' parameter is optional for if you have a mongodb database that you'd like to link to the client):
```json
{
    "email": "your_email@address.com",
    "password": "your_password",
    "mongo": "optional_mongo_uri"
}
```
* Third: create a python file like so:
```python
import aiohttp
import asyncio
import logging
import sys
import ALPC as AL

logging.root.setLevel(logging.INFO)

async def main():
    async with aiohttp.ClientSession() as session:
        print('Logging in...')
        await AL.Game.loginJSONFile(session, '..\credentials.json')
        print('Successfully logged in!')
        print('Getting G Data...')
        await AL.Game.getGData(session, True, True)
        print('Obtained G Data!')
        print('Preparing pathfinder...')
        await AL.Pathfinder.prepare(AL.Game.G)
        print('Pathfinder prepared!')
        print('Starting character...')
        char = await AL.Game.startCharacter(session, 'WarriorSurge', 'US', 'I')
        print('Moving to main...')
        await char.smartMove('main')
        print('Moving to halloween...')
        await char.smartMove('halloween')
        print('Moving to desertland...')
        await char.smartMove('desertland')
        print('Returning to main...')
        await char.smartMove('main')
        print('Disconnecting...')
        await char.disconnect()

# this part is technically only required if you're running on windows due to hinkyness involving windows OS and asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
asyncio.run(main())
```
* Fourth: run your python file; you should get this as a result:
```
Logging in...
Successfully logged in!
Getting G Data...
Obtained G Data!
Preparing pathfinder...
Pathfinder prepared!
Starting character...
Moving to main...
Moving to halloween...
Moving to desertland...
Returning to main...
Disconnecting...
```

## Version History
0.1.0: basic functionality; initial release
0.2.0: added all of the individual character classes
0.3.0: added database functionality

## Final Notes
* AS STATED, THIS PACKAGE IS STILL A WORK IN PROGRESS. If you have ANY issues at all or any suggestions or come accross any bugs, feel free to either submit them to the issues tab or submit your info to the existing issue if your bug/issue/suggestion is already there.
* The current largest bug I have is as follows:
  1. Pathfinder takes FAR too long to prepare. We've sped it up by 3 seconds with the most recent update; but it's still not enough.
  Any help with bugs (both found and not found) would be very much appreciated.