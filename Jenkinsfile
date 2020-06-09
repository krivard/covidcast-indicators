/* import shared library */
@Library('jenkins-pipeline-shared-library')_

pipeline {
    agent any
    stages {
        stage('Build') {
            steps {
                echo 'Building...' // Do some work here...
            }
        }

        stage('Test') {
            steps {
                echo 'Testing...' // Do some work here...
            }
        }

        stage('Deploy') {
            steps {
                echo 'Deploying...' // Do some work here...
            }
        }
    }

    post {
            always {
    	    /* Use slackNotifier.groovy from shared library and provide current build result as parameter */   
                slackNotifier(currentBuild.currentResult)
                cleanWs()
        }
    }
}
