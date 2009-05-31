import os.path

def ensureDirectoryExists(dirname):
	if not os.path.exists(dirname): os.makedirs(dirname)