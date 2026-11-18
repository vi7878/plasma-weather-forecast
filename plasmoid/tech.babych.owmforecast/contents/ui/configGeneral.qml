import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.kirigami as Kirigami

Kirigami.FormLayout {
    id: page
    property alias cfg_defaultCity: defaultCityField.text
    property alias cfg_refreshInterval: refreshSpinBox.value

    ListModel { id: suggestionsModel }

    Timer {
        id: debounceTimer
        interval: 350
        repeat: false
        onTriggered: page.fetchSuggestions(defaultCityField.text)
    }

    function fetchSuggestions(query) {
        var q = query.trim().split(",")[0].trim()
        if (q.length < 2) {
            suggestionsModel.clear()
            return
        }
        var xhr = new XMLHttpRequest()
        xhr.open("GET", "http://localhost:8000/api/suggest?q=" + encodeURIComponent(q), true)
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                try {
                    var resp = JSON.parse(xhr.responseText)
                    suggestionsModel.clear()
                    for (var i = 0; i < resp.suggestions.length; i++) {
                        suggestionsModel.append(resp.suggestions[i])
                    }
                } catch (e) {}
            }
        }
        xhr.send()
    }

    ColumnLayout {
        Kirigami.FormData.label: "Місто за замовчуванням:"
        Layout.fillWidth: true
        spacing: Kirigami.Units.smallSpacing

        QQC2.TextField {
            id: defaultCityField
            Layout.fillWidth: true
            placeholderText: "Введіть місто (Черкаси, Івано-Франківськ)"
            onTextEdited: debounceTimer.restart()
        }

        ColumnLayout {
            Layout.fillWidth: true
            visible: suggestionsModel.count > 0
            spacing: 2

            QQC2.Label {
                text: "Оберіть область зі списку знайдених:"
                font.pointSize: Kirigami.Theme.smallFont.pointSize
                opacity: 0.75
            }

            Repeater {
                model: suggestionsModel
                delegate: QQC2.ItemDelegate {
                    Layout.fillWidth: true
                    text: model.label
                    onClicked: {
                        defaultCityField.text = model.label
                        suggestionsModel.clear()
                    }
                }
            }
        }
    }

    QQC2.SpinBox {
        id: refreshSpinBox
        Kirigami.FormData.label: "Інтервал оновлення (сек, мін. 30):"
        from: 30
        to: 3600
        stepSize: 10
        editable: true
    }
}
