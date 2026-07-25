pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls

ApplicationWindow {
    id: root
    width: 1180
    height: 760
    minimumWidth: 1000
    minimumHeight: 680
    visible: true
    color: root.bg
    title: "SauceBoyz · Spicetify Manager"
    opacity: 0

    property bool highContrast: backend.accessibilityMode === "High contrast"
    property real interfaceFactor: backend.interfaceScale === "90%"
                                           ? 0.9
                                           : backend.interfaceScale === "110%"
                                             ? 1.1 : 1.0
    property real fontScale: root.interfaceFactor
                             * (backend.accessibilityMode === "Large text"
                                ? 1.12 : 1.0)
    property color bg: root.highContrast ? "#000000" : "#080C16"
    property color sidebar: root.highContrast ? "#050505" : "#0C1220"
    property color card: root.highContrast ? "#0C0C0C" : "#111A2C"
    property color cardHover: root.highContrast ? "#191919" : "#17243B"
    property color border: root.highContrast ? "#7D8DA8" : "#233451"
    property color textPrimary: "#FFFFFF"
    property color textMuted: root.highContrast ? "#D2D9E6" : "#98A7C2"
    property color blue: root.highContrast ? "#83ADFF" : "#6694FF"
    property color green: root.highContrast ? "#42F582" : "#25E06F"
    property color orange: "#FFB95C"
    property color purple: "#A485FF"
    property color red: "#FF647C"
    property int currentPage: 0
    property string toastText: ""
    property string toastKind: "success"
    property bool toastVisible: false
    property string pendingConfirmationAction: ""
    property var navigation: [
        { "icon": "⌂", "label": "Dashboard", "title": "Dashboard", "subtitle": "Everything you need to keep Spicetify healthy." },
        { "icon": "≡", "label": "Activity logs", "title": "Activity logs", "subtitle": "Search, review, and export command history." },
        { "icon": "?", "label": "Help center", "title": "Help center", "subtitle": "Clear answers for every action in the manager." },
        { "icon": "✦", "label": "Setup & install", "title": "Setup & install", "subtitle": "Prepare Spotify and Spicetify without guesswork." },
        { "icon": "⚙", "label": "Settings", "title": "Settings", "subtitle": "Tune the interface and application behavior." }
    ]

    function motionDuration(value) {
        return backend.animationsEnabled ? value : 0
    }

    Behavior on opacity {
        NumberAnimation { duration: root.motionDuration(180); easing.type: Easing.OutCubic }
    }

    Component.onCompleted: opacity = 1
    onCurrentPageChanged: {
        pageSwap.restart()
        if (currentPage === 1)
            backend.refreshLogs()
        else if (currentPage === 3)
            backend.refreshSetup()
    }

    SequentialAnimation {
        id: pageSwap
        NumberAnimation {
            target: pageArea
            property: "opacity"
            to: 0
            duration: root.motionDuration(70)
            easing.type: Easing.InCubic
        }
        ScriptAction {
            script: {
                pageArea.displayedPage = root.currentPage
                pageArea.x = 42
            }
        }
        ParallelAnimation {
            NumberAnimation {
                target: pageArea
                property: "opacity"
                to: 1
                duration: root.motionDuration(150)
                easing.type: Easing.OutCubic
            }
            NumberAnimation {
                target: pageArea
                property: "x"
                to: 34
                duration: root.motionDuration(150)
                easing.type: Easing.OutCubic
            }
        }
    }

    function showToast(message, kind) {
        toastText = message
        toastKind = kind || "success"
        toastVisible = true
        toastTimer.restart()
    }

    Connections {
        target: backend
        function onToastRequested(message, kind) {
            root.showToast(message, kind)
        }
        function onConfirmationRequested(title, message, action) {
            confirmationDialog.title = title
            confirmationText.text = message
            root.pendingConfirmationAction = action
            confirmationDialog.open()
        }
        function onErrorRequested(title, message) {
            errorDialog.title = title
            errorText.text = message
            errorDialog.open()
        }
    }

    Timer {
        id: toastTimer
        interval: backend.notificationDurationMs
        onTriggered: root.toastVisible = false
    }

    component SmoothButton: Rectangle {
        id: smoothButton
        property string label: ""
        property color accent: root.blue
        property bool outlined: false
        property bool interactive: true
        signal clicked()
        width: 118
        height: 38
        radius: 11
        opacity: smoothButton.interactive ? 1 : 0.48
        color: buttonMouse.pressed
               ? Qt.darker(accent, 1.18)
               : buttonMouse.containsMouse
                 ? (outlined ? root.cardHover : Qt.lighter(accent, 1.08))
                 : (outlined ? root.card : accent)
        border.width: outlined ? 1 : 0
        border.color: accent
        scale: buttonMouse.pressed ? 0.975 : 1

        Behavior on color { ColorAnimation { duration: root.motionDuration(90) } }
        Behavior on scale { NumberAnimation { duration: root.motionDuration(70); easing.type: Easing.OutCubic } }

        Text {
            anchors.centerIn: parent
            text: smoothButton.label
            color: root.textPrimary
            font.family: "Segoe UI Variable Display"
            font.pixelSize: Math.round(13 * root.fontScale)
            font.weight: Font.DemiBold
        }

        MouseArea {
            id: buttonMouse
            anchors.fill: parent
            enabled: smoothButton.interactive
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: smoothButton.clicked()
        }
    }

    component NavButton: Item {
        id: navButton
        required property int navIndex
        required property string navIcon
        required property string navLabel
        width: 192
        height: 46

        Rectangle {
            anchors.fill: parent
            radius: 12
            color: navButton.navIndex === root.currentPage
                   ? root.card
                   : navMouse.containsMouse
                     ? "#111A2A"
                     : "transparent"
            Behavior on color { ColorAnimation { duration: root.motionDuration(90) } }
        }

        Text {
            x: 17
            anchors.verticalCenter: parent.verticalCenter
            text: navButton.navIcon
            color: navButton.navIndex === root.currentPage ? root.textPrimary : root.textMuted
            font.family: "Segoe UI Symbol"
            font.pixelSize: Math.round(15 * root.fontScale)
            Behavior on color { ColorAnimation { duration: root.motionDuration(90) } }
        }

        Text {
            x: 44
            anchors.verticalCenter: parent.verticalCenter
            text: navButton.navLabel
            color: navButton.navIndex === root.currentPage ? root.textPrimary : root.textMuted
            font.family: "Segoe UI Variable Display"
            font.pixelSize: Math.round(14 * root.fontScale)
            font.weight: Font.DemiBold
            Behavior on color { ColorAnimation { duration: root.motionDuration(90) } }
        }

        MouseArea {
            id: navMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: root.currentPage = navButton.navIndex
        }
    }

    component ActionCard: Rectangle {
        id: actionCard
        required property string titleText
        required property string detailText
        required property color accent
        required property string actionName
        property bool interactive: !backend.busy
        width: 430
        height: 74
        radius: 16
        color: actionMouse.containsMouse ? root.cardHover : root.card
        border.width: 1
        border.color: actionMouse.containsMouse ? accent : root.border
        scale: actionMouse.pressed ? 0.985 : 1

        opacity: actionCard.interactive ? 1 : 0.55
        Behavior on color { ColorAnimation { duration: root.motionDuration(100) } }
        Behavior on border.color { ColorAnimation { duration: root.motionDuration(100) } }
        Behavior on scale { NumberAnimation { duration: root.motionDuration(70); easing.type: Easing.OutCubic } }

        Rectangle {
            x: 20
            anchors.verticalCenter: parent.verticalCenter
            width: 10
            height: 10
            radius: 5
            color: actionCard.accent
        }

        Text {
            x: 50
            y: 17
            text: actionCard.titleText
            color: root.textPrimary
            font.family: "Segoe UI Variable Display"
            font.pixelSize: Math.round(14 * root.fontScale)
            font.weight: Font.DemiBold
        }

        Text {
            x: 50
            y: 42
            text: actionCard.detailText
            color: root.textMuted
            font.family: "Segoe UI Variable Text"
            font.pixelSize: Math.round(12 * root.fontScale)
        }

        Rectangle {
            width: 36
            height: 36
            radius: 11
            anchors.right: parent.right
            anchors.rightMargin: 17
            anchors.verticalCenter: parent.verticalCenter
            color: actionMouse.containsMouse ? actionCard.accent : "#17233A"
            border.width: 1
            border.color: actionMouse.containsMouse ? actionCard.accent : root.border
            Behavior on color { ColorAnimation { duration: root.motionDuration(100) } }

            Text {
                anchors.centerIn: parent
                text: "→"
                color: root.textPrimary
                font.pixelSize: Math.round(19 * root.fontScale)
            }
        }

        MouseArea {
            id: actionMouse
            anchors.fill: parent
            enabled: actionCard.interactive
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: backend.runAction(actionCard.actionName)
        }
    }

    component DarkField: TextField {
        id: darkField
        color: root.textPrimary
        placeholderTextColor: "#71809B"
        selectionColor: root.blue
        selectedTextColor: root.textPrimary
        font.family: "Cascadia Mono"
        font.pixelSize: Math.round(12 * root.fontScale)
        leftPadding: 14
        rightPadding: 14
        background: Rectangle {
            radius: 11
            color: root.bg
            border.width: 1
            border.color: darkField.activeFocus ? root.blue : root.border
            Behavior on border.color {
                ColorAnimation { duration: root.motionDuration(90) }
            }
        }
    }

    component DarkCombo: ComboBox {
        id: darkCombo
        height: 40
        leftPadding: 13
        rightPadding: 34
        font.family: "Segoe UI Variable Text"
        font.pixelSize: Math.round(12 * root.fontScale)

        contentItem: Text {
            leftPadding: 0
            rightPadding: 0
            text: darkCombo.displayText
            color: root.textPrimary
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
            font: darkCombo.font
        }

        indicator: Text {
            x: darkCombo.width - width - 13
            anchors.verticalCenter: parent.verticalCenter
            text: "⌄"
            color: root.textMuted
            font.pixelSize: Math.round(16 * root.fontScale)
        }

        background: Rectangle {
            radius: 11
            color: root.bg
            border.width: 1
            border.color: darkCombo.activeFocus ? root.blue : root.border
        }

        delegate: ItemDelegate {
            id: comboItem
            required property var modelData
            required property int index
            width: darkCombo.width
            height: 36
            contentItem: Text {
                text: comboItem.modelData
                color: comboItem.highlighted ? root.textPrimary : root.textMuted
                verticalAlignment: Text.AlignVCenter
                font: darkCombo.font
            }
            highlighted: darkCombo.highlightedIndex === index
            background: Rectangle {
                radius: 7
                color: comboItem.highlighted ? root.cardHover : "transparent"
            }
        }

        popup: Popup {
            y: darkCombo.height + 4
            width: darkCombo.width
            implicitHeight: Math.min(contentItem.implicitHeight + 8, 250)
            padding: 4
            contentItem: ListView {
                clip: true
                implicitHeight: contentHeight
                model: darkCombo.popup.visible ? darkCombo.delegateModel : null
                currentIndex: darkCombo.highlightedIndex
                ScrollIndicator.vertical: ScrollIndicator { }
            }
            background: Rectangle {
                radius: 11
                color: "#10192A"
                border.width: 1
                border.color: root.border
            }
        }
    }

    component ToggleSwitch: Rectangle {
        id: toggleSwitch
        property bool checked: false
        signal toggled(bool value)
        width: 48
        height: 26
        radius: 13
        color: checked ? root.green : "#26334A"

        Behavior on color {
            ColorAnimation { duration: root.motionDuration(110) }
        }

        Rectangle {
            width: 20
            height: 20
            radius: 10
            y: 3
            x: toggleSwitch.checked ? 25 : 3
            color: root.textPrimary
            Behavior on x {
                NumberAnimation {
                    duration: root.motionDuration(120)
                    easing.type: Easing.OutCubic
                }
            }
        }

        MouseArea {
            anchors.fill: parent
            cursorShape: Qt.PointingHandCursor
            onClicked: toggleSwitch.toggled(!toggleSwitch.checked)
        }
    }

    component SettingRow: Rectangle {
        id: settingRow
        required property string titleText
        required property string detailText
        default property alias control: controlHost.data
        width: 700
        height: 78
        radius: 16
        color: root.card
        border.width: 1
        border.color: root.border

        Text {
            x: 18
            y: 15
            text: settingRow.titleText
            color: root.textPrimary
            font.family: "Segoe UI Variable Display"
            font.pixelSize: Math.round(14 * root.fontScale)
            font.weight: Font.DemiBold
        }
        Text {
            x: 18
            y: 43
            width: settingRow.width - controlHost.width - 58
            text: settingRow.detailText
            color: root.textMuted
            elide: Text.ElideRight
            font.family: "Segoe UI Variable Text"
            font.pixelSize: Math.round(12 * root.fontScale)
        }
        Item {
            id: controlHost
            width: 190
            height: parent.height
            anchors.right: parent.right
            anchors.rightMargin: 18
        }
    }

    component SetupActionCard: Rectangle {
        id: setupCard
        required property string titleText
        required property string detailText
        required property string buttonText
        required property string actionName
        property color accent: root.blue
        property bool interactive: true
        width: 430
        height: 92
        radius: 17
        color: setupMouse.containsMouse && interactive
               ? root.cardHover : root.card
        border.width: 1
        border.color: setupMouse.containsMouse && interactive
                      ? accent : root.border
        opacity: interactive ? 1 : 0.48
        scale: setupMouse.pressed ? 0.988 : 1
        Behavior on color {
            ColorAnimation { duration: root.motionDuration(100) }
        }
        Behavior on border.color {
            ColorAnimation { duration: root.motionDuration(100) }
        }
        Behavior on scale {
            NumberAnimation { duration: root.motionDuration(70) }
        }

        Rectangle {
            x: 18
            anchors.verticalCenter: parent.verticalCenter
            width: 10
            height: 48
            radius: 5
            color: setupCard.accent
        }
        Text {
            x: 42
            y: 19
            text: setupCard.titleText
            color: root.textPrimary
            font.family: "Segoe UI Variable Display"
            font.pixelSize: Math.round(14 * root.fontScale)
            font.weight: Font.DemiBold
        }
        Text {
            x: 42
            y: 48
            width: parent.width - 178
            text: setupCard.detailText
            color: root.textMuted
            elide: Text.ElideRight
            font.family: "Segoe UI Variable Text"
            font.pixelSize: Math.round(11 * root.fontScale)
        }
        Rectangle {
            width: 92
            height: 36
            radius: 10
            anchors.right: parent.right
            anchors.rightMargin: 17
            anchors.verticalCenter: parent.verticalCenter
            color: setupCard.accent
            Text {
                anchors.centerIn: parent
                text: setupCard.buttonText
                color: root.textPrimary
                font.family: "Segoe UI Variable Display"
                font.pixelSize: Math.round(12 * root.fontScale)
                font.weight: Font.DemiBold
            }
        }
        MouseArea {
            id: setupMouse
            anchors.fill: parent
            enabled: setupCard.interactive && !backend.busy
            hoverEnabled: true
            cursorShape: Qt.PointingHandCursor
            onClicked: backend.setupAction(setupCard.actionName)
        }
    }

    Rectangle {
        id: sidebarPanel
        width: 224
        anchors.top: parent.top
        anchors.bottom: parent.bottom
        anchors.left: parent.left
        color: root.sidebar

        Image {
            x: 22
            y: 23
            width: 43
            height: 43
            source: appIconUrl
            fillMode: Image.PreserveAspectFit
            mipmap: true
        }

        Text {
            x: 76
            y: 27
            text: "SauceBoyz"
            color: root.textPrimary
            font.family: "Segoe UI Variable Display"
            font.pixelSize: Math.round(20 * root.fontScale)
            font.weight: Font.Bold
        }

        Text {
            x: 77
            y: 52
            text: "SPICETIFY MANAGER"
            color: root.textMuted
            font.family: "Segoe UI Variable Text"
            font.pixelSize: Math.round(10 * root.fontScale)
            font.letterSpacing: 0.8
            font.weight: Font.DemiBold
        }

        Rectangle {
            x: 0
            y: 129 + root.currentPage * 54
            width: 4
            height: 38
            radius: 2
            color: root.green

            Behavior on y {
                NumberAnimation { duration: 130; easing.type: Easing.OutCubic }
            }
        }

        Column {
            x: 16
            y: 125
            spacing: 8

            Repeater {
                model: root.navigation
                delegate: NavButton {
                    required property var modelData
                    required property int index
                    navIndex: index
                    navIcon: modelData.icon
                    navLabel: modelData.label
                }
            }
        }

        Rectangle {
            x: 18
            width: 188
            height: 86
            radius: 16
            anchors.bottom: parent.bottom
            anchors.bottomMargin: 22
            color: root.card
            border.width: 1
            border.color: root.border

            Image {
                x: 15
                anchors.verticalCenter: parent.verticalCenter
                width: 34
                height: 34
                source: appIconUrl
                fillMode: Image.PreserveAspectFit
                mipmap: true
            }

            Text {
                x: 58
                y: 24
                text: "Spicetify Manager"
                color: root.textPrimary
                font.family: "Segoe UI Variable Display"
                font.pixelSize: Math.round(12 * root.fontScale)
                font.weight: Font.DemiBold
            }

            Text {
                x: 58
                y: 47
                text: "Version v" + appVersion
                color: root.textMuted
                font.family: "Segoe UI Variable Text"
                font.pixelSize: Math.round(11 * root.fontScale)
            }
        }
    }

    Item {
        id: workspace
        anchors.left: sidebarPanel.right
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.bottom: parent.bottom

        Text {
            x: 34
            y: 25
            text: root.navigation[root.currentPage].title
            color: root.textPrimary
            font.family: "Segoe UI Variable Display"
            font.pixelSize: Math.round(31 * root.fontScale)
            font.weight: Font.Bold
        }

        Text {
            x: 35
            y: 69
            text: root.navigation[root.currentPage].subtitle
            color: root.textMuted
            font.family: "Segoe UI Variable Text"
            font.pixelSize: Math.round(13 * root.fontScale)
        }

        Rectangle {
            width: 106
            height: 34
            radius: 17
            anchors.right: parent.right
            anchors.rightMargin: 34
            y: 37
            color: "#101B30"

            Rectangle {
                x: 26
                anchors.verticalCenter: parent.verticalCenter
                width: 7
                height: 7
                radius: 4
                color: backend.busy ? root.orange : root.green
                Behavior on color { ColorAnimation { duration: 120 } }
            }

            Text {
                x: 41
                anchors.verticalCenter: parent.verticalCenter
                text: backend.busy ? "Running" : "Ready"
                color: backend.busy ? root.orange : root.green
                font.family: "Segoe UI Variable Display"
                font.pixelSize: Math.round(12 * root.fontScale)
                font.weight: Font.DemiBold
                Behavior on color { ColorAnimation { duration: 120 } }
            }
        }

        Item {
            id: pageArea
            property int displayedPage: 0
            x: 34
            y: 96
            width: parent.width - 68
            height: parent.height - 122

            Item {
                id: dashboardPage
                anchors.fill: parent
                visible: pageArea.displayedPage === 0
                enabled: visible

                Rectangle {
                    id: statusCard
                    width: parent.width
                    height: 120
                    radius: 19
                    color: root.card
                    border.width: 1
                    border.color: root.border

                    Text {
                        x: 22
                        y: 18
                        text: "SPICETIFY STATUS"
                        color: root.textMuted
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: Math.round(10 * root.fontScale)
                        font.weight: Font.Bold
                        font.letterSpacing: 0.8
                    }

                    Text {
                        x: 22
                        y: 45
                        width: statusCard.width * 0.37
                        elide: Text.ElideRight
                        text: backend.cliTitle
                        color: root.textPrimary
                        font.family: "Segoe UI Variable Display"
                        font.pixelSize: Math.round(21 * root.fontScale)
                        font.weight: Font.DemiBold
                    }

                    Text {
                        x: 22
                        y: 80
                        width: statusCard.width * 0.37
                        elide: Text.ElideRight
                        text: backend.cliDetail
                        color: root.textMuted
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: Math.round(12 * root.fontScale)
                    }

                    Rectangle {
                        x: statusCard.width * 0.42
                        y: 18
                        width: 1
                        height: 84
                        color: root.border
                    }

                    Text {
                        x: statusCard.width * 0.45
                        y: 18
                        text: "MARKETPLACE STATUS"
                        color: root.textMuted
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: Math.round(10 * root.fontScale)
                        font.weight: Font.Bold
                        font.letterSpacing: 0.8
                    }

                    Text {
                        x: statusCard.width * 0.45
                        y: 45
                        width: statusCard.width * 0.34
                        elide: Text.ElideRight
                        text: backend.marketplaceTitle
                        color: root.textPrimary
                        font.family: "Segoe UI Variable Display"
                        font.pixelSize: Math.round(18 * root.fontScale)
                        font.weight: Font.DemiBold
                    }

                    Text {
                        x: statusCard.width * 0.45
                        y: 80
                        width: statusCard.width * 0.34
                        elide: Text.ElideRight
                        text: backend.marketplaceDetail
                        color: root.textMuted
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: Math.round(12 * root.fontScale)
                    }

                    SmoothButton {
                        anchors.right: parent.right
                        anchors.rightMargin: 20
                        y: 20
                        height: 36
                        label: backend.busy ? "Checking…" : "Check all"
                        accent: root.blue
                        outlined: true
                        interactive: !backend.busy
                        onClicked: backend.refreshAll()
                    }

                    SmoothButton {
                        anchors.right: parent.right
                        anchors.rightMargin: 20
                        y: 64
                        height: 36
                        label: backend.marketplaceActionLabel
                        accent: root.green
                        outlined: true
                        interactive: backend.marketplaceActionEnabled
                        onClicked: backend.marketplaceAction()
                    }
                }

                Grid {
                    id: actionGrid
                    anchors.top: statusCard.bottom
                    anchors.topMargin: 12
                    width: parent.width
                    columns: 2
                    columnSpacing: 12
                    rowSpacing: 10

                    ActionCard {
                        width: (actionGrid.width - 12) / 2
                        titleText: "Update theme"
                        detailText: "Hot-reload active theme changes"
                        accent: root.blue
                        actionName: "update"
                    }
                    ActionCard {
                        width: (actionGrid.width - 12) / 2
                        titleText: "Upgrade CLI"
                        detailText: "Install the newest Spicetify release"
                        accent: root.green
                        actionName: "upgrade"
                    }
                    ActionCard {
                        width: (actionGrid.width - 12) / 2
                        titleText: "Backup & apply"
                        detailText: "Reapply after a Spotify update"
                        accent: root.purple
                        actionName: "backup"
                    }
                    ActionCard {
                        width: (actionGrid.width - 12) / 2
                        titleText: "Restore Spotify"
                        detailText: "Return Spotify to its original state"
                        accent: root.orange
                        actionName: "restore"
                    }
                }

                Rectangle {
                    id: consoleCard
                    anchors.top: actionGrid.bottom
                    anchors.topMargin: 12
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    radius: 19
                    color: root.card
                    border.width: 1
                    border.color: root.border

                    Text {
                        x: 20
                        y: 16
                        text: "Command console"
                        color: root.textPrimary
                        font.family: "Segoe UI Variable Display"
                        font.pixelSize: Math.round(15 * root.fontScale)
                        font.weight: Font.DemiBold
                    }

                    DarkField {
                        id: commandField
                        x: 18
                        y: 48
                        width: parent.width - 192
                        height: 40
                        enabled: !backend.busy
                        placeholderText: "Enter a command, for example: spicetify config"
                        onAccepted: backend.runCustomCommand(text)
                    }

                    SmoothButton {
                        x: parent.width - 158
                        y: 49
                        width: 66
                        height: 38
                        label: "Run"
                        accent: root.blue
                        interactive: !backend.busy
                        onClicked: backend.runCustomCommand(commandField.text)
                    }

                    SmoothButton {
                        x: parent.width - 84
                        y: 49
                        width: 66
                        height: 38
                        label: "Cancel"
                        accent: root.red
                        outlined: true
                        interactive: backend.busy
                        onClicked: backend.cancelOperation()
                    }

                    Rectangle {
                        x: 18
                        y: 98
                        width: parent.width - 36
                        height: parent.height - 158
                        radius: 12
                        color: "#080D17"

                        ScrollView {
                            anchors.fill: parent
                            anchors.margins: 8
                            clip: true

                            TextArea {
                                id: consoleOutput
                                readOnly: true
                                text: backend.consoleText
                                color: "#B7C3D8"
                                selectionColor: root.blue
                                selectedTextColor: root.textPrimary
                                wrapMode: TextEdit.Wrap
                                font.family: "Cascadia Mono"
                                font.pixelSize: Math.round(12 * root.fontScale)
                                background: null
                                onTextChanged: cursorPosition = length
                            }
                        }
                    }

                    Text {
                        x: 20
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 17
                        text: backend.operationLabel
                        color: backend.operationState === "success"
                               ? root.green
                               : backend.operationState === "error"
                                 ? root.red
                                 : backend.operationState === "warning"
                                   ? root.orange
                                   : backend.busy
                                     ? root.blue
                                     : root.textMuted
                        font.family: "Segoe UI Variable Display"
                        font.pixelSize: Math.round(12 * root.fontScale)
                        font.weight: Font.DemiBold
                        Behavior on color {
                            ColorAnimation { duration: root.motionDuration(100) }
                        }
                    }

                    Item {
                        width: 260
                        height: 24
                        anchors.right: parent.right
                        anchors.rightMargin: 20
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 10
                        opacity: backend.progressVisible ? 1 : 0
                        visible: opacity > 0
                        Behavior on opacity {
                            NumberAnimation {
                                duration: root.motionDuration(140)
                            }
                        }

                        Rectangle {
                            width: 220
                            height: 7
                            radius: 4
                            anchors.left: parent.left
                            anchors.verticalCenter: parent.verticalCenter
                            color: "#26334A"

                            Rectangle {
                                width: parent.width * backend.progress
                                height: parent.height
                                radius: parent.radius
                                color: backend.operationState === "error"
                                       ? root.red : root.green
                                Behavior on width {
                                    NumberAnimation {
                                        duration: root.motionDuration(160)
                                        easing.type: Easing.OutCubic
                                    }
                                }
                            }
                        }

                        Text {
                            anchors.right: parent.right
                            anchors.verticalCenter: parent.verticalCenter
                            text: backend.progressPercent + "%"
                            color: root.textMuted
                            font.family: "Cascadia Mono"
                            font.pixelSize: Math.round(11 * root.fontScale)
                            font.weight: Font.DemiBold
                        }
                    }
                }
            }

            Item {
                id: logsPage
                anchors.fill: parent
                visible: pageArea.displayedPage === 1
                enabled: visible

                Rectangle {
                    id: logToolbar
                    width: parent.width
                    height: 62
                    radius: 16
                    color: root.card
                    border.width: 1
                    border.color: root.border

                    Text {
                        x: 18
                        anchors.verticalCenter: parent.verticalCenter
                        text: "Session"
                        color: root.textMuted
                        font.family: "Segoe UI Variable Display"
                        font.pixelSize: Math.round(12 * root.fontScale)
                        font.weight: Font.DemiBold
                    }

                    DarkCombo {
                        id: logSessionCombo
                        x: 78
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.min(300, parent.width * 0.32)
                        model: backend.logSessions
                        currentIndex: Math.max(
                            0, backend.logSessions.indexOf(backend.selectedLog)
                        )
                        onActivated: backend.loadLog(
                            currentText, logSearch.text
                        )
                    }

                    DarkField {
                        id: logSearch
                        x: logSessionCombo.x + logSessionCombo.width + 12
                        anchors.verticalCenter: parent.verticalCenter
                        width: Math.min(230, parent.width * 0.25)
                        height: 40
                        placeholderText: "Search this log"
                        onTextChanged: backend.loadLog(
                            logSessionCombo.currentText, text
                        )
                    }

                    SmoothButton {
                        anchors.right: openLogFolderButton.left
                        anchors.rightMargin: 10
                        anchors.verticalCenter: parent.verticalCenter
                        width: 90
                        label: "Refresh"
                        outlined: true
                        onClicked: backend.refreshLogs()
                    }
                    SmoothButton {
                        id: openLogFolderButton
                        anchors.right: parent.right
                        anchors.rightMargin: 12
                        anchors.verticalCenter: parent.verticalCenter
                        width: 112
                        label: "Open folder"
                        outlined: true
                        onClicked: backend.openLogsFolder()
                    }
                }

                Rectangle {
                    anchors.top: logToolbar.bottom
                    anchors.topMargin: 12
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: logActions.top
                    anchors.bottomMargin: 12
                    radius: 16
                    color: "#080D17"
                    border.width: 1
                    border.color: root.border

                    ScrollView {
                        anchors.fill: parent
                        anchors.margins: 10
                        clip: true
                        TextArea {
                            readOnly: true
                            text: backend.logContent
                            color: "#C2CCDD"
                            selectionColor: root.blue
                            selectedTextColor: root.textPrimary
                            wrapMode: TextEdit.Wrap
                            font.family: "Cascadia Mono"
                            font.pixelSize: Math.round(12 * root.fontScale)
                            background: null
                        }
                    }
                }

                Row {
                    id: logActions
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    spacing: 10

                    SmoothButton {
                        width: 104
                        label: "Save copy"
                        outlined: true
                        onClicked: backend.saveLogCopy()
                    }
                    SmoothButton {
                        width: 104
                        label: "Clear log"
                        accent: root.orange
                        outlined: true
                        onClicked: backend.requestLogAction("clear")
                    }
                    SmoothButton {
                        width: 104
                        label: "Delete log"
                        accent: root.red
                        outlined: true
                        onClicked: backend.requestLogAction("delete")
                    }
                }
            }

            Item {
                id: helpPage
                anchors.fill: parent
                visible: pageArea.displayedPage === 2
                enabled: visible
                property string selectedCategory: "All"
                property var helpEntries: [
                    {
                        "category": "Commands",
                        "title": "First setup or after a Spotify update",
                        "description": "Creates a fresh Spotify backup and applies your themes, extensions, and custom apps.",
                        "command": "spicetify backup apply",
                        "accent": root.green
                    },
                    {
                        "category": "Commands",
                        "title": "Apply your current configuration",
                        "description": "Applies the selected theme, color scheme, extensions, and custom apps to Spotify.",
                        "command": "spicetify apply",
                        "accent": root.blue
                    },
                    {
                        "category": "Commands",
                        "title": "Hot-reload theme changes",
                        "description": "Refreshes an active theme while you are editing it. Press Ctrl + Shift + R in Spotify afterward.",
                        "command": "spicetify update",
                        "accent": root.purple
                    },
                    {
                        "category": "Commands",
                        "title": "Upgrade the Spicetify CLI",
                        "description": "Installs the latest CLI release when Spicetify was installed with the official script.",
                        "command": "spicetify upgrade",
                        "accent": root.green
                    },
                    {
                        "category": "Commands",
                        "title": "View or edit configuration",
                        "description": "Shows every current setting. Add a setting and value to change it.",
                        "command": "spicetify config",
                        "accent": root.blue
                    },
                    {
                        "category": "Commands",
                        "title": "Open the configuration folder",
                        "description": "Opens your Spicetify folder in File Explorer.",
                        "command": "spicetify config-dir",
                        "accent": root.orange
                    },
                    {
                        "category": "Commands",
                        "title": "Find important Spicetify paths",
                        "description": "Prints the config and Spotify installation locations detected by the CLI.",
                        "command": "spicetify path",
                        "accent": root.orange
                    },
                    {
                        "category": "Commands",
                        "title": "Get command help",
                        "description": "Lists commands and flags. Add a command name for more specific help.",
                        "command": "spicetify --help",
                        "accent": root.blue
                    },
                    {
                        "category": "Fixes",
                        "title": "Fully restore and reapply",
                        "description": "Use this when the backup no longer matches Spotify or a normal apply does not recover it.",
                        "command": "spicetify restore backup apply",
                        "accent": root.orange
                    },
                    {
                        "category": "Fixes",
                        "title": "Return Spotify to its original state",
                        "description": "Removes Spicetify modifications while preserving your configuration and customization files.",
                        "command": "spicetify restore",
                        "accent": root.red
                    },
                    {
                        "category": "Fixes",
                        "title": "Show the configuration file path",
                        "description": "Useful when Spotify's prefs file or another saved path needs to be corrected.",
                        "command": "spicetify -c",
                        "accent": root.orange
                    }
                ]
                property var resourceEntries: [
                    {
                        "category": "Docs",
                        "title": "Getting Started",
                        "description": "Official installation and first-time setup guide.",
                        "url": "https://spicetify.app/docs/getting-started",
                        "badge": "SPICETIFY"
                    },
                    {
                        "category": "Docs",
                        "title": "Complete CLI command reference",
                        "description": "Every official command, option, example, and combined workflow.",
                        "url": "https://spicetify.app/docs/cli/commands",
                        "badge": "SPICETIFY"
                    },
                    {
                        "category": "Docs",
                        "title": "FAQ and troubleshooting",
                        "description": "Official fixes for config paths, Spotify updates, prefs errors, and common problems.",
                        "url": "https://spicetify.app/docs/faq",
                        "badge": "SPICETIFY"
                    },
                    {
                        "category": "Docs",
                        "title": "Spicetify CLI on GitHub",
                        "description": "Releases, source code, issues, and project announcements.",
                        "url": "https://github.com/spicetify/cli",
                        "badge": "GITHUB"
                    },
                    {
                        "category": "Docs",
                        "title": "Marketplace installation",
                        "description": "Official Marketplace installation and manual setup instructions.",
                        "url": "https://github.com/spicetify/marketplace/wiki/Installation",
                        "badge": "MARKETPLACE"
                    },
                    {
                        "category": "Docs",
                        "title": "Spotify desktop download",
                        "description": "Download the supported desktop installer directly from Spotify.",
                        "url": "https://www.spotify.com/download/windows/",
                        "badge": "SPOTIFY"
                    }
                ]

                function textMatches(entry) {
                    var query = helpSearch.text.trim().toLowerCase()
                    if (query.length === 0)
                        return true
                    return (entry.title + " " + entry.description + " "
                            + (entry.command || "") + " " + (entry.badge || ""))
                            .toLowerCase().indexOf(query) >= 0
                }

                function entryVisible(entry) {
                    return (selectedCategory === "All"
                            || selectedCategory === entry.category)
                            && textMatches(entry)
                }

                function hasVisibleEntries() {
                    for (var index = 0; index < helpEntries.length; ++index) {
                        if (entryVisible(helpEntries[index]))
                            return true
                    }
                    for (var resourceIndex = 0;
                         resourceIndex < resourceEntries.length;
                         ++resourceIndex) {
                        if (entryVisible(resourceEntries[resourceIndex]))
                            return true
                    }
                    return false
                }

                function hasVisibleGroup(entries) {
                    for (var index = 0; index < entries.length; ++index) {
                        if (entryVisible(entries[index]))
                            return true
                    }
                    return false
                }

                Rectangle {
                    id: helpTools
                    width: parent.width
                    height: 82
                    radius: 17
                    color: root.card
                    border.width: 1
                    border.color: root.border

                    DarkField {
                        id: helpSearch
                        x: 16
                        y: 14
                        width: parent.width - categoryRow.width - 48
                        height: 40
                        placeholderText: "Search commands, fixes, or documentation"
                    }

                    Row {
                        id: categoryRow
                        anchors.right: parent.right
                        anchors.rightMargin: 16
                        y: 14
                        spacing: 7

                        Repeater {
                            model: ["All", "Commands", "Fixes", "Docs"]
                            delegate: Rectangle {
                                id: categoryChip
                                required property string modelData
                                width: modelData === "Commands" ? 92 : 65
                                height: 40
                                radius: 11
                                color: helpPage.selectedCategory === modelData
                                       ? root.blue
                                       : chipMouse.containsMouse
                                         ? root.cardHover : root.bg
                                border.width: helpPage.selectedCategory === modelData ? 0 : 1
                                border.color: root.border
                                Behavior on color {
                                    ColorAnimation { duration: root.motionDuration(90) }
                                }

                                Text {
                                    anchors.centerIn: parent
                                    text: categoryChip.modelData
                                    color: root.textPrimary
                                    font.family: "Segoe UI Variable Display"
                                    font.pixelSize: Math.round(12 * root.fontScale)
                                    font.weight: Font.DemiBold
                                }
                                MouseArea {
                                    id: chipMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: helpPage.selectedCategory = categoryChip.modelData
                                }
                            }
                        }
                    }

                    Text {
                        x: 18
                        anchors.bottom: parent.bottom
                        anchors.bottomMargin: 8
                        text: "Copy a command, or open a verified official resource."
                        color: root.textMuted
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: Math.round(11 * root.fontScale)
                    }
                }

                ScrollView {
                    anchors.top: helpTools.bottom
                    anchors.topMargin: 12
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    clip: true
                    contentWidth: availableWidth

                    Column {
                        width: helpPage.width
                        spacing: 10

                        Text {
                            visible: helpPage.hasVisibleGroup(helpPage.helpEntries)
                            height: visible ? 30 : 0
                            text: helpPage.selectedCategory === "Fixes"
                                  ? "Troubleshooting commands"
                                  : "Useful commands"
                            color: root.textPrimary
                            font.family: "Segoe UI Variable Display"
                            font.pixelSize: Math.round(16 * root.fontScale)
                            font.weight: Font.DemiBold
                            verticalAlignment: Text.AlignVCenter
                        }

                        Repeater {
                            model: helpPage.helpEntries

                            delegate: Rectangle {
                                id: commandHelpCard
                                required property var modelData
                                visible: helpPage.entryVisible(modelData)
                                width: helpPage.width
                                height: visible ? 104 : 0
                                radius: 16
                                color: commandMouse.containsMouse ? root.cardHover : root.card
                                border.width: 1
                                border.color: root.border
                                Behavior on color {
                                    ColorAnimation { duration: root.motionDuration(90) }
                                }

                                Rectangle {
                                    x: 17
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 7
                                    height: 66
                                    radius: 4
                                    color: commandHelpCard.modelData.accent
                                }
                                Text {
                                    x: 42
                                    y: 12
                                    width: parent.width - 190
                                    text: commandHelpCard.modelData.title
                                    color: root.textPrimary
                                    font.family: "Segoe UI Variable Display"
                                    font.pixelSize: Math.round(14 * root.fontScale)
                                    font.weight: Font.DemiBold
                                }
                                Text {
                                    x: 42
                                    y: 36
                                    width: parent.width - 190
                                    text: commandHelpCard.modelData.description
                                    color: root.textMuted
                                    wrapMode: Text.Wrap
                                    font.family: "Segoe UI Variable Text"
                                    font.pixelSize: Math.round(11 * root.fontScale)
                                }
                                Rectangle {
                                    x: 42
                                    anchors.bottom: parent.bottom
                                    anchors.bottomMargin: 11
                                    width: Math.min(commandText.implicitWidth + 24,
                                                    parent.width - 190)
                                    height: 27
                                    radius: 8
                                    color: root.bg
                                    border.width: 1
                                    border.color: root.border
                                    Text {
                                        id: commandText
                                        anchors.centerIn: parent
                                        text: commandHelpCard.modelData.command
                                        color: root.textPrimary
                                        font.family: "Cascadia Mono"
                                        font.pixelSize: Math.round(11 * root.fontScale)
                                    }
                                }
                                SmoothButton {
                                    anchors.right: parent.right
                                    anchors.rightMargin: 15
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 112
                                    label: "Copy"
                                    accent: commandHelpCard.modelData.accent
                                    outlined: true
                                    onClicked: backend.copyHelpCommand(
                                                   commandHelpCard.modelData.command)
                                }
                                MouseArea {
                                    id: commandMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    acceptedButtons: Qt.NoButton
                                }
                            }
                        }

                        Text {
                            visible: helpPage.hasVisibleGroup(
                                         helpPage.resourceEntries)
                            height: visible ? 38 : 0
                            text: "Official documentation"
                            color: root.textPrimary
                            font.family: "Segoe UI Variable Display"
                            font.pixelSize: Math.round(16 * root.fontScale)
                            font.weight: Font.DemiBold
                            verticalAlignment: Text.AlignBottom
                        }

                        Repeater {
                            model: helpPage.resourceEntries
                            delegate: Rectangle {
                                id: resourceCard
                                required property var modelData
                                visible: helpPage.entryVisible(modelData)
                                width: helpPage.width
                                height: visible ? 78 : 0
                                radius: 16
                                color: resourceMouse.containsMouse
                                       ? root.cardHover : root.card
                                border.width: 1
                                border.color: root.border
                                Behavior on color {
                                    ColorAnimation { duration: root.motionDuration(90) }
                                }

                                Rectangle {
                                    x: 16
                                    anchors.verticalCenter: parent.verticalCenter
                                    width: 104
                                    height: 28
                                    radius: 8
                                    color: root.bg
                                    border.width: 1
                                    border.color: root.border
                                    Text {
                                        anchors.centerIn: parent
                                        text: resourceCard.modelData.badge
                                        color: root.blue
                                        font.family: "Segoe UI Variable Display"
                                        font.pixelSize: Math.round(10 * root.fontScale)
                                        font.weight: Font.DemiBold
                                    }
                                }
                                Text {
                                    x: 138
                                    y: 13
                                    width: parent.width - 300
                                    text: resourceCard.modelData.title
                                    color: root.textPrimary
                                    font.family: "Segoe UI Variable Display"
                                    font.pixelSize: Math.round(14 * root.fontScale)
                                    font.weight: Font.DemiBold
                                }
                                Text {
                                    x: 138
                                    y: 39
                                    width: parent.width - 300
                                    text: resourceCard.modelData.description
                                    color: root.textMuted
                                    elide: Text.ElideRight
                                    font.family: "Segoe UI Variable Text"
                                    font.pixelSize: Math.round(11 * root.fontScale)
                                }
                                Text {
                                    anchors.right: parent.right
                                    anchors.rightMargin: 18
                                    anchors.verticalCenter: parent.verticalCenter
                                    text: "Open  ↗"
                                    color: root.blue
                                    font.family: "Segoe UI Variable Display"
                                    font.pixelSize: Math.round(13 * root.fontScale)
                                    font.weight: Font.DemiBold
                                }
                                MouseArea {
                                    id: resourceMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: backend.openHelpLink(
                                                   resourceCard.modelData.url)
                                }
                            }
                        }

                        Rectangle {
                            visible: !helpPage.hasVisibleEntries()
                            width: helpPage.width
                            height: visible ? 120 : 0
                            radius: 16
                            color: root.card
                            border.width: 1
                            border.color: root.border
                            Text {
                                anchors.centerIn: parent
                                text: "No help results match “" + helpSearch.text + "”"
                                color: root.textMuted
                                font.family: "Segoe UI Variable Text"
                                font.pixelSize: Math.round(13 * root.fontScale)
                            }
                        }
                    }
                }
            }

            Item {
                id: setupPage
                anchors.fill: parent
                visible: pageArea.displayedPage === 3
                enabled: visible

                Rectangle {
                    id: detectionCard
                    width: parent.width
                    height: 104
                    radius: 18
                    color: root.card
                    border.width: 1
                    border.color: root.border

                    Rectangle {
                        x: parent.width / 2
                        y: 17
                        width: 1
                        height: 70
                        color: root.border
                    }

                    Text {
                        x: 20
                        y: 18
                        width: parent.width * 0.42
                        text: backend.spotifyTitle
                        color: backend.spotifySupported
                               ? root.green : root.orange
                        elide: Text.ElideRight
                        font.family: "Segoe UI Variable Display"
                        font.pixelSize: Math.round(15 * root.fontScale)
                        font.weight: Font.DemiBold
                    }
                    Text {
                        x: 20
                        y: 52
                        width: parent.width * 0.42
                        text: backend.spotifyDetail
                        color: root.textMuted
                        elide: Text.ElideMiddle
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: Math.round(12 * root.fontScale)
                    }
                    Text {
                        x: parent.width / 2 + 22
                        y: 18
                        width: parent.width * 0.35
                        text: backend.spicetifySetupTitle
                        color: backend.spicetifyInstalled
                               ? root.green : root.orange
                        elide: Text.ElideRight
                        font.family: "Segoe UI Variable Display"
                        font.pixelSize: Math.round(15 * root.fontScale)
                        font.weight: Font.DemiBold
                    }
                    Text {
                        x: parent.width / 2 + 22
                        y: 52
                        width: parent.width * 0.35
                        text: backend.spicetifySetupDetail
                        color: root.textMuted
                        elide: Text.ElideMiddle
                        font.family: "Segoe UI Variable Text"
                        font.pixelSize: Math.round(12 * root.fontScale)
                    }
                    SmoothButton {
                        anchors.right: parent.right
                        anchors.rightMargin: 18
                        anchors.verticalCenter: parent.verticalCenter
                        width: 90
                        label: "Detect"
                        outlined: true
                        interactive: !backend.busy
                        onClicked: backend.refreshSetup()
                    }
                }

                Grid {
                    id: setupGrid
                    anchors.top: detectionCard.bottom
                    anchors.topMargin: 12
                    width: parent.width
                    columns: 2
                    columnSpacing: 12
                    rowSpacing: 10

                    SetupActionCard {
                        width: (setupGrid.width - 12) / 2
                        titleText: "Install Spicetify"
                        detailText: "Download and run the official Windows installer."
                        buttonText: backend.spicetifyInstalled ? "Installed" : "Install"
                        actionName: "install"
                        accent: root.green
                        interactive: !backend.spicetifyInstalled
                    }
                    SetupActionCard {
                        width: (setupGrid.width - 12) / 2
                        titleText: "Download Spotify"
                        detailText: "Open the official desktop Spotify download."
                        buttonText: backend.spotifySupported ? "Ready" : "Download"
                        actionName: "spotify"
                        accent: root.blue
                        interactive: !backend.spotifySupported
                    }
                    SetupActionCard {
                        width: (setupGrid.width - 12) / 2
                        titleText: "First-time setup"
                        detailText: "Create a clean backup and apply Spicetify."
                        buttonText: "Set up"
                        actionName: "first"
                        accent: root.purple
                        interactive: backend.spicetifyInstalled
                                     && backend.spotifySupported
                    }
                    SetupActionCard {
                        width: (setupGrid.width - 12) / 2
                        titleText: "Repair installation"
                        detailText: "Restore, rebuild the backup, and reapply."
                        buttonText: "Repair"
                        actionName: "repair"
                        accent: root.orange
                        interactive: backend.spicetifyInstalled
                                     && backend.spotifySupported
                    }
                    SetupActionCard {
                        width: (setupGrid.width - 12) / 2
                        titleText: "Remove modifications"
                        detailText: "Return Spotify to its original state."
                        buttonText: "Restore"
                        actionName: "restore"
                        accent: root.orange
                        interactive: backend.spicetifyInstalled
                    }
                    SetupActionCard {
                        width: (setupGrid.width - 12) / 2
                        titleText: "Fully uninstall Spicetify"
                        detailText: "Remove the CLI, configuration, themes, and extensions."
                        buttonText: "Uninstall"
                        actionName: "uninstall"
                        accent: root.red
                        interactive: backend.spicetifyInstalled
                    }
                }
            }

            Item {
                id: settingsPage
                anchors.fill: parent
                visible: pageArea.displayedPage === 4
                enabled: visible

                ScrollView {
                    anchors.fill: parent
                    clip: true
                    contentWidth: availableWidth

                    Column {
                        width: settingsPage.width
                        spacing: 10

                        SettingRow {
                            width: settingsPage.width
                            titleText: "Interface motion"
                            detailText: "Smooth navigation, progress movement, and status feedback."
                            ToggleSwitch {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                checked: backend.animationsEnabled
                                onToggled: backend.setSetting(
                                    "animations_enabled", value
                                )
                            }
                        }

                        SettingRow {
                            width: settingsPage.width
                            titleText: "Notification timer"
                            detailText: "How long completion messages and the 100% progress bar remain visible."
                            DarkCombo {
                                width: 150
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                model: ["2 seconds", "3 seconds", "5 seconds", "8 seconds"]
                                currentIndex: model.indexOf(
                                    backend.notificationDuration
                                )
                                onActivated: backend.setSetting(
                                    "notification_duration", currentText
                                )
                            }
                        }

                        SettingRow {
                            width: settingsPage.width
                            titleText: "Always on top"
                            detailText: "Keep Spicetify Manager above other windows."
                            ToggleSwitch {
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                checked: backend.alwaysOnTop
                                onToggled: backend.setSetting(
                                    "always_on_top", value
                                )
                            }
                        }

                        SettingRow {
                            width: settingsPage.width
                            titleText: "Interface size"
                            detailText: "Choose the comfortable size for controls and text."
                            DarkCombo {
                                width: 150
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                model: ["90%", "100%", "110%"]
                                currentIndex: model.indexOf(
                                    backend.interfaceScale
                                )
                                onActivated: backend.setSetting(
                                    "interface_scale", currentText
                                )
                            }
                        }

                        SettingRow {
                            width: settingsPage.width
                            titleText: "Accessibility"
                            detailText: "Use standard, larger text, or a higher-contrast palette."
                            DarkCombo {
                                width: 150
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                model: ["Standard", "Large text", "High contrast"]
                                currentIndex: model.indexOf(
                                    backend.accessibilityMode
                                )
                                onActivated: backend.setSetting(
                                    "accessibility_mode", currentText
                                )
                            }
                        }

                        SettingRow {
                            width: settingsPage.width
                            titleText: "Application updates"
                            detailText: backend.appUpdateDetail
                            SmoothButton {
                                width: 150
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                label: backend.appUpdateLabel
                                outlined: true
                                interactive: !backend.busy
                                onClicked: backend.checkAppUpdates()
                            }
                        }

                        SettingRow {
                            width: settingsPage.width
                            titleText: "Activity log storage"
                            detailText: backend.logFolder
                            SmoothButton {
                                width: 150
                                anchors.right: parent.right
                                anchors.verticalCenter: parent.verticalCenter
                                label: "Open folder"
                                outlined: true
                                onClicked: backend.openLogsFolder()
                            }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: confirmationDialog
        width: 480
        height: 230
        anchors.centerIn: Overlay.overlay
        modal: true
        closePolicy: Popup.CloseOnEscape
        padding: 24

        background: Rectangle {
            radius: 18
            color: "#10192A"
            border.width: 1
            border.color: root.border
        }
        header: Item {
            height: 64
            Text {
                x: 24
                anchors.verticalCenter: parent.verticalCenter
                text: confirmationDialog.title
                color: root.textPrimary
                font.family: "Segoe UI Variable Display"
                font.pixelSize: Math.round(19 * root.fontScale)
                font.weight: Font.DemiBold
            }
        }
        contentItem: Text {
            id: confirmationText
            color: root.textMuted
            wrapMode: Text.Wrap
            font.family: "Segoe UI Variable Text"
            font.pixelSize: Math.round(13 * root.fontScale)
        }
        footer: Item {
            height: 62
            SmoothButton {
                anchors.right: confirmButton.left
                anchors.rightMargin: 10
                anchors.verticalCenter: parent.verticalCenter
                width: 100
                label: "Cancel"
                outlined: true
                onClicked: confirmationDialog.reject()
            }
            SmoothButton {
                id: confirmButton
                anchors.right: parent.right
                anchors.rightMargin: 20
                anchors.verticalCenter: parent.verticalCenter
                width: 100
                label: "Continue"
                accent: root.blue
                onClicked: confirmationDialog.accept()
            }
        }
        onAccepted: {
            backend.confirmAction(root.pendingConfirmationAction)
            root.pendingConfirmationAction = ""
        }
        onRejected: root.pendingConfirmationAction = ""
    }

    Dialog {
        id: errorDialog
        width: 460
        height: 220
        anchors.centerIn: Overlay.overlay
        modal: true
        closePolicy: Popup.CloseOnEscape
        padding: 24

        background: Rectangle {
            radius: 18
            color: "#10192A"
            border.width: 1
            border.color: root.red
        }
        header: Item {
            height: 64
            Text {
                x: 24
                anchors.verticalCenter: parent.verticalCenter
                text: errorDialog.title
                color: root.textPrimary
                font.family: "Segoe UI Variable Display"
                font.pixelSize: Math.round(19 * root.fontScale)
                font.weight: Font.DemiBold
            }
        }
        contentItem: Text {
            id: errorText
            color: root.textMuted
            wrapMode: Text.Wrap
            font.family: "Segoe UI Variable Text"
            font.pixelSize: Math.round(13 * root.fontScale)
        }
        footer: Item {
            height: 62
            SmoothButton {
                anchors.right: parent.right
                anchors.rightMargin: 20
                anchors.verticalCenter: parent.verticalCenter
                width: 100
                label: "OK"
                accent: root.red
                onClicked: errorDialog.accept()
            }
        }
    }

    Rectangle {
        id: toast
        objectName: "toast"
        width: 340
        height: 64
        radius: 16
        x: root.width - width - 24
        y: root.toastVisible ? root.height - height - 24 : root.height + 12
        opacity: root.toastVisible ? 1 : 0
        color: root.cardHover
        border.width: 1
        border.color: root.toastKind === "error"
                      ? root.red
                      : root.toastKind === "warning"
                        ? root.orange : root.green
        z: 100

        Behavior on y {
            NumberAnimation { duration: 150; easing.type: Easing.OutCubic }
        }
        Behavior on opacity { NumberAnimation { duration: 110 } }

        Rectangle {
            x: 17
            anchors.verticalCenter: parent.verticalCenter
            width: 9
            height: 9
            radius: 5
            color: toast.border.color
        }

        Text {
            x: 42
            width: parent.width - 58
            anchors.verticalCenter: parent.verticalCenter
            text: root.toastText
            wrapMode: Text.Wrap
            color: root.textPrimary
            font.family: "Segoe UI Variable Text"
            font.pixelSize: Math.round(12 * root.fontScale)
        }
    }
}
