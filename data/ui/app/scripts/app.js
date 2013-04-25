'use strict';


// Declare app level module which depends on filters, and services
var ooniprobe = angular.module('ooniprobe', ['ngUpload', 'ooniprobe.services']).
  config(['$routeProvider', function($routeProvider) {

    $routeProvider.when('/inputs',
      {
        templateUrl: 'views/inputs.html',
        controller: 'InputsCtrl'
      }
    );

    $routeProvider.when('/settings',
      {
        templateUrl: 'views/settings.html',
        controller: 'SettingsCtrl'
      }
    );

    $routeProvider.when('/test/:testID',
      {
        templateUrl: 'views/test.html',
        controller: 'TestCtrl'
      }
    );

    $routeProvider.otherwise({redirectTo: '/settings'});
  }]);
