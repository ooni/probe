'use strict';


// Declare app level module which depends on filters, and services
var ooniprobe = angular.module('ooniprobe', ['ooniprobe.services']).
  config(['$routeProvider', function($routeProvider) {
    $routeProvider.when('/test-status',
      {
        templateUrl: 'views/test-status.html',
        controller: 'PageCtrl'
      }
    );

    $routeProvider.when('/test-list',
      {
        templateUrl: 'views/test-list.html',
        controller: 'TestListCtrl'
      }
    );

    $routeProvider.when('/test/:testID',
      {
        templateUrl: 'views/test-list.html',
        controller: 'TestListCtrl'
      }
    );

    $routeProvider.otherwise({redirectTo: '/test-status'});
  }]);
