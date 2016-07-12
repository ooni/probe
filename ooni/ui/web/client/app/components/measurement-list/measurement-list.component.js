var template = require("./measurement-list.html");
var controller = require("./measurement-list.controller");
require("./measurement-list.css");

module.exports = {
  restrict: 'E',
  bindings: {},
  template: template,
  controller: controller
};
