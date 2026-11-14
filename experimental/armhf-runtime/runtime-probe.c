#include <SDL.h>
#include <stdio.h>

int main(void)
{
    SDL_version version;
    SDL_GetVersion(&version);

    if (SDL_Init(0) != 0) {
        fprintf(stderr, "SDL_Init failed: %s\n", SDL_GetError());
        return 1;
    }

    printf("ARMHF dynamic loader and SDL2 loaded successfully (SDL %u.%u.%u)\n",
           version.major, version.minor, version.patch);
    SDL_Quit();
    return 0;
}
