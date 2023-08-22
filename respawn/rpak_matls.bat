:: run in Legion+1.7.0 dir
:: list all materials indexed by mapname `.rpak`s
FOR %%G IN ("D:\SteamLibrary\steamapps\common\Titanfall2\r2\paks\Win64\mp_*.rpak") DO LegionPlus.exe --fullpath --loadmaterials --list "%%G"
FOR %%G IN ("D:\SteamLibrary\steamapps\common\Titanfall2\r2\paks\Win64\sp_*.rpak") DO LegionPlus.exe --fullpath --loadmaterials --list "%%G"
