#include "pch.h"
#include <windows.h>
#include <CommCtrl.h>

// A nova função não retorna um ponteiro. Ela preenche um buffer fornecido pelo MQL4.
// Ela retorna o número de bytes que foram copiados.
extern "C" {
    __declspec(dllexport) int GetAlertBytes(char* buffer, int bufferSize) {
        // Garante que o buffer comece vazio
        if (bufferSize > 0) {
            buffer[0] = '\0';
        }

        HWND alertHwnd = FindWindowA("#32770", "Alerta");
        if (alertHwnd != NULL) {
            HWND listHwnd = FindWindowExA(alertHwnd, NULL, "SysListView32", NULL);
            if (listHwnd != NULL) {
                LVITEMA itemInfo = { 0 };
                itemInfo.mask = LVIF_TEXT;
                itemInfo.iItem = 0;
                itemInfo.iSubItem = 1;
                itemInfo.pszText = buffer; // O buffer do MQL4 é o destino direto
                itemInfo.cchTextMax = bufferSize;

                // Envia a mensagem para preencher o buffer e retorna o número de caracteres
                return SendMessageA(listHwnd, LVM_GETITEMTEXTA, 0, (LPARAM)&itemInfo);
            }
        }
        return 0; // Retorna 0 se nada foi encontrado
    }
}