# AdventureLand Python Client
This is meant to be a python client for the game [Adventure Land - The Code MMORPG](https://adventure.land). It's heavily inspired by and based on earthiverse's typescript-based [ALClient](https://github.com/earthiverse/ALClient).

Currently a major work in progress; but the current state is available through [pip](https://pypi.org/project/pip/) for simple installation and use.

## Requirements
This package currently requires `aiohttp`, `aiosignal`, `async-timeout`, `attrs`, `bidict`, `charset-normalizer`, `frozenlist`, `idna`, `igraph`, `multidict`, `python-engineio`, `setuptools`, `texttables`, `ujson`, and `yarl`. (Technially only some of these are dependencies of ALPC; others are dependencies of various dependencies).

[b]All[/b] of these requirements are installable through pip, and their individual installations are also taken care of through the install of ALPC.

## Installation
The PyPI page can be found [here]. In order to install, simply install the package using pip like so:
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

* <small>*Note: I have had personal trouble with using py on windows and the entirety of this package was developed using an installation of `python3` from the windows store; therefore, I cannot guarantee that it will work with use of the `py` command.*</small>

## Usage
* First: be sure to install the package from PyPI using pip.
* Second: create a `credentials.json` file like so:
```json
{
    'email': 'youremail@address.com',
    'password': 'yourpassword'
}
```
* Third: create a python file like so:
```python
import aiohttp
import asyncio
import logging
import ALPC as AL

logging.root.setLevel(logging.INFO)

async def main():
    async with aiohttp.ClientSession() as session:
        await AL.Game.loginJSONFile(session, '.\credentials.json')
        await AL.Game.getGData(session, True, True)
        await AL.Pathfinder.prepare(AL.Game.G)
        char = await AL.Game.startCharacter(session, 'YourCharacterName', 'US', 'I')
        print('Moving to main)
        await char.smartMove('main')
        print('Moving to forest')
        await char.smartMove('halloween')
        print('Moving to desertland')
        await char.smartMove('desertland')
        print('Returning to main')
        await char.smartMove('main')
        print('Disconnecting...')
        await char.disconnect()

asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()) # if you're running on windows, include this line
asyncio.run(main())
```
* Fourth: run your python file; you should get this as a result:
```
TO BE CONTINUED...
```
