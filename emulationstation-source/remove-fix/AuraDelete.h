#pragma once
#include "guis/GuiLoading.h"
#include "guis/GuiMsgBox.h"
#include "views/ViewController.h"
#include <fstream>
#include <sstream>
#include <spawn.h>
#include <sys/wait.h>
#include <cerrno>
extern char **environ;
inline bool auraManaged(const std::string& path) {
    if(path.find("/userdata/roms/apps/")!=0 && path.find("/userdata/roms/ports/")!=0) return false;
    return path.size()>4 && (path.substr(path.size()-3)==".sh" || path.substr(path.size()-4)==".app");
}
inline void auraDelete(Window* window, FileData* file, std::function<void()> normal) {
    const auto path=file->getSourceFileData()->getPath();
    if(!auraManaged(path)) {normal();return;}
    window->pushGui(new GuiMsgBox(window,"Remover este atalho? Se for um aplicativo Flatpak gerenciado pelo Aura, ele e seus dados locais tambem serao desinstalados.",
        "REMOVER",[window,path,normal] {
            window->pushGui(new GuiLoading<int>(window,"Desinstalando aplicativo...",
                [path](IGuiLoadingHandler*) {
                    const char* args[]={"python3","/userdata/system/aura-store-native/remove_app.py","--path",path.c_str(),nullptr};
                    pid_t pid;int status=0;
                    if(posix_spawnp(&pid,"python3",nullptr,nullptr,const_cast<char**>(args),environ)!=0)return 1;
                    while(waitpid(pid,&status,0)<0)if(errno!=EINTR)return 1;
                    return WIFEXITED(status)?WEXITSTATUS(status):1;
                },[window,normal](int result) {
                    if(result==0) { ViewController::reloadAllGames(window,false,false,false); }
                    else window->pushGui(new GuiMsgBox(window,"Nao foi possivel desinstalar. O atalho foi mantido. Consulte remove-app.log na pasta da loja."));
                }));
        },"CANCELAR",nullptr));
}
