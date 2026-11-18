import QtQuick
import QtQuick.Layouts
import QtQuick.Controls as QQC2
import org.kde.plasma.plasmoid
import org.kde.plasma.components as PlasmaComponents3
import org.kde.plasma.extras as PlasmaExtras
import org.kde.kirigami as Kirigami

PlasmoidItem {
    id: root
    width: Kirigami.Units.gridUnit * 24
    height: Kirigami.Units.gridUnit * 28

    preferredRepresentation: fullRepresentation

    readonly property string apiBaseUrl: "http://localhost:8000"
    property int refreshSeconds: Math.max(30, Plasmoid.configuration.refreshInterval || 60)
    property string errorMessage: ""
    property bool isLoading: false
    property bool showHistoryPopup: false
    property string currentQueryText: ""
    property string activeCityQuery: Plasmoid.configuration.defaultCity || "Cherkasy"
    property var activeLat: undefined
    property var activeLon: undefined
    property string activeState: ""
    property int activeCityId: 0

    ListModel { id: citiesModel }
    ListModel { id: forecastsModel }
    ListModel { id: suggestionsModel }

    Timer {
        id: suggestTimer
        interval: 350
        repeat: false
        onTriggered: root.fetchSuggestions(root.currentQueryText)
    }

    Timer {
        id: autoRefreshTimer
        interval: root.refreshSeconds * 1000
        running: true
        repeat: true
        onTriggered: {
            if (!root.isLoading && root.activeCityQuery !== "") {
                root.syncWithApi(root.activeCityQuery, root.activeLat, root.activeLon, root.activeState, true)
            }
        }
    }

    Component.onCompleted: {
        loadSavedCities()
    }

    function fetchSuggestions(query) {
        var q = query.trim().split(",")[0].trim()
        if (q.length < 2) {
            suggestionsModel.clear()
            return
        }
        var xhr = new XMLHttpRequest()
        xhr.open("GET", apiBaseUrl + "/api/suggest?q=" + encodeURIComponent(q), true)
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

    function syncWithApi(cityName, lat, lon, state, isAutoRefresh) {
        if (!cityName || cityName.trim() === "") {
            if (!isAutoRefresh) {
                errorMessage = "Помилка: введіть назву міста!"
            }
            return
        }
        activeCityQuery = cityName.trim()
        activeLat = lat
        activeLon = lon
        activeState = state || ""
        suggestionsModel.clear()
        showHistoryPopup = false
        isLoading = true
        errorMessage = ""

        var xhr = new XMLHttpRequest()
        var url = apiBaseUrl + "/api/sync?city=" + encodeURIComponent(cityName.trim())
        if (lat !== undefined && lon !== undefined) {
            url += "&lat=" + encodeURIComponent(lat) + "&lon=" + encodeURIComponent(lon)
        }
        if (state) {
            url += "&state=" + encodeURIComponent(state)
        }
        xhr.open("POST", url, true)
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                isLoading = false
                if (xhr.status === 200) {
                    try {
                        var resp = JSON.parse(xhr.responseText)
                        activeCityId = resp.city.city_id
                        errorMessage = ""
                        loadSavedCities(resp.city.city_id)
                    } catch (e) {
                        errorMessage = "Помилка обробки даних прогнозу"
                    }
                } else if (xhr.status === 0) {
                    errorMessage = "Сервіс погоди недоступний"
                } else {
                    try {
                        var err = JSON.parse(xhr.responseText)
                        errorMessage = err.detail || ("Помилка: статус " + xhr.status)
                    } catch (e) {
                        errorMessage = "Помилка HTTP: статус " + xhr.status
                    }
                }
            }
        }
        xhr.send()
    }

    function loadSavedCities(selectCityId) {
        var xhr = new XMLHttpRequest()
        xhr.open("GET", apiBaseUrl + "/api/cities", true)
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                if (xhr.status === 200) {
                    errorMessage = ""
                    var resp = JSON.parse(xhr.responseText)
                    citiesModel.clear()
                    var targetIndex = 0
                    for (var i = 0; i < resp.cities.length; i++) {
                        var c = resp.cities[i]
                        citiesModel.append({
                            "cityId": c.id,
                            "cityName": c.name,
                            "label": c.name + " (" + c.country + ")"
                        })
                        if (selectCityId && c.id === selectCityId) {
                            targetIndex = i
                        }
                    }
                    if (citiesModel.count > 0) {
                        var chosen = citiesModel.get(targetIndex)
                        activeCityId = chosen.cityId
                        activeCityQuery = chosen.cityName
                        loadForecastsFromDb(chosen.cityId)
                    }
                } else if (xhr.status === 0) {
                    errorMessage = "Сервіс погоди не запущено"
                }
            }
        }
        xhr.send()
    }

    function loadForecastsFromDb(cityId) {
        if (!cityId) return
        var xhr = new XMLHttpRequest()
        xhr.open("GET", apiBaseUrl + "/api/forecasts/" + cityId, true)
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                var resp = JSON.parse(xhr.responseText)
                forecastsModel.clear()
                for (var i = 0; i < resp.forecasts.length; i++) {
                    var f = resp.forecasts[i]
                    forecastsModel.append({
                        "time": String(f.forecast_time).replace("T", " "),
                        "temp": Number(f.temp).toFixed(1) + " °C",
                        "feels": "Відчувається: " + Number(f.feels_like).toFixed(1) + " °C",
                        "humidity": f.humidity + "%",
                        "desc": f.description,
                        "wind": f.wind_speed + " м/с"
                    })
                }
            }
        }
        xhr.send()
    }

    fullRepresentation: PlasmaExtras.Representation {
        collapseMarginsHint: true

        header: PlasmaExtras.PlasmoidHeading {
            ColumnLayout {
                anchors.fill: parent
                spacing: Kirigami.Units.smallSpacing

                RowLayout {
                    Layout.fillWidth: true
                    PlasmaComponents3.TextField {
                        id: cityInput
                        Layout.fillWidth: true
                        placeholderText: "Введіть місто (Черкаси, Івано-Франківськ)"
                        onActiveFocusChanged: {
                            if (activeFocus) {
                                root.loadSavedCities(root.activeCityId)
                                root.showHistoryPopup = true
                            }
                        }
                        MouseArea {
                            anchors.fill: parent
                            acceptedButtons: Qt.LeftButton
                            onPressed: function(mouse) {
                                cityInput.forceActiveFocus()
                                root.showHistoryPopup = true
                                mouse.accepted = false
                            }
                        }
                        onTextEdited: {
                            root.currentQueryText = cityInput.text
                            root.showHistoryPopup = (cityInput.text.trim().length < 2)
                            suggestTimer.restart()
                        }
                        onAccepted: root.syncWithApi(cityInput.text)
                    }
                    PlasmaComponents3.Button {
                        icon.name: "view-refresh"
                        text: "Оновити прогноз"
                        enabled: !root.isLoading
                        onClicked: root.syncWithApi(cityInput.text)
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    visible: suggestionsModel.count > 0
                    spacing: 2

                    Repeater {
                        model: suggestionsModel
                        delegate: PlasmaComponents3.ItemDelegate {
                            Layout.fillWidth: true
                            text: model.label
                            onClicked: {
                                cityInput.text = model.label
                                root.syncWithApi(model.name, model.lat, model.lon, model.state)
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    visible: root.showHistoryPopup && suggestionsModel.count === 0 && citiesModel.count > 0
                    spacing: 2

                    RowLayout {
                        Layout.fillWidth: true
                        PlasmaComponents3.Label {
                            Layout.fillWidth: true
                            text: "Історія запитів:"
                            font.pointSize: Kirigami.Theme.smallFont.pointSize
                            opacity: 0.75
                        }
                        PlasmaComponents3.ToolButton {
                            icon.name: "window-close"
                            implicitWidth: Kirigami.Units.gridUnit * 1.2
                            implicitHeight: Kirigami.Units.gridUnit * 1.2
                            onClicked: root.showHistoryPopup = false
                        }
                    }

                    Repeater {
                        model: citiesModel
                        delegate: PlasmaComponents3.ItemDelegate {
                            Layout.fillWidth: true
                            text: model.label
                            onClicked: {
                                cityInput.text = model.cityName
                                root.activeCityId = model.cityId
                                root.activeCityQuery = model.cityName
                                root.activeLat = undefined
                                root.activeLon = undefined
                                root.activeState = ""
                                root.showHistoryPopup = false
                                root.errorMessage = ""
                                root.loadForecastsFromDb(model.cityId)
                            }
                        }
                    }
                }

                PlasmaComponents3.Label {
                    Layout.fillWidth: true
                    visible: root.errorMessage !== ""
                    text: root.errorMessage
                    wrapMode: Text.WordWrap
                    font.pointSize: Kirigami.Theme.smallFont.pointSize
                    color: Kirigami.Theme.negativeTextColor
                }
            }
        }

        contentItem: QQC2.ScrollView {
            ListView {
                id: forecastList
                model: forecastsModel
                clip: true
                spacing: Kirigami.Units.smallSpacing
                onMovementStarted: root.showHistoryPopup = false

                delegate: Kirigami.AbstractCard {
                    width: forecastList.width - Kirigami.Units.largeSpacing
                    contentItem: RowLayout {
                        spacing: Kirigami.Units.largeSpacing

                        ColumnLayout {
                            Layout.preferredWidth: Kirigami.Units.gridUnit * 7
                            PlasmaComponents3.Label {
                                text: model.time
                                font.bold: true
                            }
                            PlasmaComponents3.Label {
                                text: model.desc
                                font.capitalization: Font.Capitalize
                                opacity: 0.8
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            PlasmaComponents3.Label {
                                text: model.temp
                                font.pointSize: Kirigami.Theme.defaultFont.pointSize * 1.2
                                font.bold: true
                                color: Kirigami.Theme.highlightColor
                            }
                            PlasmaComponents3.Label {
                                text: model.feels
                                font.pointSize: Kirigami.Theme.smallFont.pointSize
                                opacity: 0.75
                            }
                        }

                        ColumnLayout {
                            Layout.alignment: Qt.AlignRight
                            PlasmaComponents3.Label {
                                text: "💧 " + model.humidity
                            }
                            PlasmaComponents3.Label {
                                text: "💨 " + model.wind
                            }
                        }
                    }
                }
            }
        }
    }
}
