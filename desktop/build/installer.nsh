# Script NSIS custom, inclus automatiquement par electron-builder
# (buildResources/installer.nsh → cf. NsisTarget : getResource(…, "installer.nsh")).

# Remplace le contrôle « l'app tourne-t-elle ? » d'electron-builder.
#
# Pourquoi : l'app vit dans la zone de notification et démarre masquée à
# l'ouverture de session (setLoginItemSettings openAsHidden), donc elle tourne
# à presque chaque installation — sans fenêtre visible. Le contrôle par défaut
# tente alors un `taskkill` sans /f, qui se contente d'envoyer WM_CLOSE : la
# fenêtre se masque, le process reste. L'installeur affiche
# « ${PRODUCT_NAME} is running », puis « impossible de fermer l'app », et
# abandonne l'installation — l'ancienne version reste en place.
#
# On ferme donc directement, sans dialogue. L'app ne garde aucun état non
# persisté côté process principal (les réglages sont écrits au fur et à mesure
# dans config.json, la file offline vit dans le renderer).
#
# $R0 est libre ici : l'implémentation par défaut le clobbe au même endroit.
!macro customCheckAppRunning
  DetailPrint "Fermeture de ${PRODUCT_NAME}..."
  nsExec::Exec `"$SYSDIR\taskkill.exe" /f /im "${APP_EXECUTABLE_FILENAME}"`
  Pop $R0
  # Laisse Windows relâcher les verrous de fichiers avant la copie.
  Sleep 1000
!macroend
