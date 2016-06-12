;(function() {


  angular
    .module('ooniprobe', [
      'ngRoute'
    ])
    .config(config);

    config.$inject = ['$routeProvider', '$locationProvider',
                      '$httpProvider', '$compileProvider'];

    function config($routeProvider, $locationProvider,
                    $httpProvider, $compileProvider) {

      $routeProvider.when('/settings',
        {
          templateUrl: '/static/views/settings.html',
          controller: 'MainCtrl'
        }
      )
      .when('/',
        {
          templateUrl: '/static/views/home.html',
          controller: 'MainCtrl'
        }
      )
      .when('/net-tests/:testName?',
        {
          templateUrl: '/static/views/net-tests.html',
          controller: 'NetTestCtrl'
        }
      )
      .otherwise({
        redirectTo: '/'
      });

      // This avoid having the leading # in the address bar
      //$locationProvider.html5Mode(true);
    }

    angular
      .module('ooniprobe')
      .run(run);

    run.$inject = ['$rootScope', '$location'];

    function run($rootScope, $location) {
      console.log("running.");
    }

})();
