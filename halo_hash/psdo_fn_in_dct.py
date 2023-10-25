from time import sleep


def scene_2(**dat):
    dat['fn'] = scene_1
    print("scene_2")
    return dat


def scene_1(**dat):
    dat['fn'] = scene_2
    print("scene_1")
    return dat


def execute_strategy(**dat):
    """
        we deal with only on trade here
    """
    while (
        (dat.get('fn', 'COMPLETE') != 'COMPLETE')
    ):
        # we empty the fn key here so next time
        # around, if it is empty, we will exit
        # the thread
        current_function = dat.pop('fn')
        # the current_function == scene_1
        dat = current_function(**dat)
        sleep(1)
    else:
        print("end of thread")


dat = {'fn': scene_1}
execute_strategy(**dat)
