var angular = require("angular");
var Nettest = require("./nettest/nettest")
var Measurement = require("./measurement/measurement");
var MeasurementList = require("./measurement-list/measurement-list");
var MeasurementSummary = require("./measurement-summary/measurement-summary");

var componentsModule = angular.module("app.components", [
  Nettest,
  Measurement,
  MeasurementList,
  MeasurementSummary
])
.name;

module.exports = componentsModule;
