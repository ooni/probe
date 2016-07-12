var template = require("./measurement-summary.html");
var controller = require("./measurement-summary.controller");
require("./measurement-summary.css");

module.exports = {
  restrict: 'E',
  bindings: {},
  template: template,
  controller: controller
};
