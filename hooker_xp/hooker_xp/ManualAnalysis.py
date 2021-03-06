# -*- coding: utf-8 -*-
#+---------------------------------------------------------------------------+
#|                                                                           |
#|                          Android's Hooker                                 |
#|                                                                           |
#+---------------------------------------------------------------------------+
#| Copyright (C) 2011 Georges Bossert and Dimitri Kirchner                   |
#| This program is free software: you can redistribute it and/or modify      |
#| it under the terms of the GNU General Public License as published by      |
#| the Free Software Foundation, either version 3 of the License, or         |
#| (at your option) any later version.                                       |
#|                                                                           |
#| This program is distributed in the hope that it will be useful,           |
#| but WITHOUT ANY WARRANTY; without even the implied warranty of            |
#| MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the              |
#| GNU General Public License for more details.                              |
#|                                                                           |
#| You should have received a copy of the GNU General Public License         |
#| along with this program. If not, see <http://www.gnu.org/licenses/>.      |
#+---------------------------------------------------------------------------+
#| @url      : http://www.amossys.fr                                         |
#| @contact  : android-hooker@amossys.fr                                     |
#| @sponsors : Amossys, http://www.amossys.fr                                |
#+---------------------------------------------------------------------------+

#+---------------------------------------------------------------------------+
#| Standard library imports
#+---------------------------------------------------------------------------+
import os
import time

#+---------------------------------------------------------------------------+
#| Local imports
#+---------------------------------------------------------------------------+
from hooker_common import Logger
from hooker_xp.analysis.Analysis import Analysis
from hooker_xp.analysis.ManualAnalysisConfiguration import ManualAnalysisConfiguration
from hooker_xp.report.ReportingConfiguration import ReportingConfiguration
from hooker_xp.analysis.MainConfiguration import MainConfiguration
from hooker_xp.analysis.StaticAnalysis import StaticAnalysis

class ManualAnalysis(Analysis):
    """Executes a single analysis of an Android application.
    The user will be prompted to stimulate the application once the
    android emulator is started. The analysis stops when the emulator is closed by the user. A report is then returned.
    """

    def __init__(self, commandLineParser):
        super(ManualAnalysis, self).__init__(MainConfiguration.build(commandLineParser), ReportingConfiguration.build(commandLineParser), )
        self._logger = Logger.getLogger(__name__)
        self.analysisConfiguration = self.__prepareAnalysis(commandLineParser)
        
    def start(self):
        """Starts the current manual analysis"""

        if self.mainConfiguration is None:
            raise Exception("No main configuration found, cannot start the analysis..")

        if self.reportingConfiguration is None:
            raise Exception("No reporting configuration found, cannot start the analysis.")
        
        if self.analysisConfiguration is None:
            raise Exception("No analysis configuration found, cannot start the analysis.")

        self._logger.info(str(self))

        # Build the identifier experiment
        idXp = self._generateIdXp(self.analysisConfiguration.apkFiles)

        # Targeted APK
        analyzedAPKFile = self.analysisConfiguration.apkFiles[0]
        
        # Execute the analysis on the first emulator
        iEmulator = 0
        emulatorName = "Emulator_{0}".format(iEmulator)
        
        # Create a new report for this analysis
        Analysis.createReport(self.reporter, idXp, emulatorName, "unknown", analyzedAPKFile, "manual", None)

        # Execute static analysis
        staticAnalysis = StaticAnalysis(analyzedAPKFile, self.mainConfiguration, self.reporter, idXp)

        Analysis.reportEvent(self.reporter, idXp, "Analysis", "Executing Static Analysis on {0}".format(analyzedAPKFile))        
        staticAnalysis.execute()
        self._logger.info(staticAnalysis)
        
        Analysis.reportEvent(self.reporter, idXp, "Emulator", "creation of the Emulator {0}".format(emulatorName))
        emulator = self._createEmulator(iEmulator, emulatorName)        

        if emulator is None:
            raise Exception("Something has prevented the creation of an emulator.")

        # Starts the emulator
        Analysis.reportEvent(self.reporter, idXp, "Emulator", "start")
        emulator.start()

        # Install preparation applications
        for prepareAPK in self.analysisConfiguration.prepareAPKs:
            Analysis.reportEvent(self.reporter, idXp, "Emulator", "installAPK", prepareAPK)
            emulator.installAPK(prepareAPK)

        # Execute preparation applications
        for prepareAPK in self.analysisConfiguration.prepareAPKs:
            Analysis.reportEvent(self.reporter, idXp, "Emulator", "startActivity", os.path.basename(prepareAPK)[:-4])
            emulator.startActivity(os.path.basename(prepareAPK)[:-4])        

        # Writes the experiment configuration on the emulator
        Analysis.reportEvent(self.reporter, idXp, "Emulator", "writeConfiguration")
        self._writeConfigurationOnEmulator(emulator, idXp)

        sleepDuration = 30
        self._logger.debug("Waiting {0} seconds for the emulator to prepare...".format(sleepDuration))
        time.sleep(sleepDuration)
        
        # Install the targeted application
        for analysisAPK in self.analysisConfiguration.apkFiles:
            Analysis.reportEvent(self.reporter, idXp, "Emulator", "installAPK", analysisAPK)
            emulator.installAPK(analysisAPK)

        Analysis.reportEvent(self.reporter, idXp, "Emulator", "Launching main activity", staticAnalysis.mainActivity)
        self._logger.info("Starting main activity: {0}".format(staticAnalysis.mainActivity))
        emulator.startActivityFromPackage(staticAnalysis.packageName, staticAnalysis.mainActivity)

        # The user is now requested to perform any operations he wants
        # this script waits for the emulator process to be closed
        self._logger.info("Proceed to the stimulation of the environnment.")
        self._logger.info("Once achieved, close the emulator and waits for the hooker to finish.")
        Analysis.reportEvent(self.reporter, idXp, "Emulator", "waitToBeClosed")
        
        emulator.waitToBeClosed()

        Analysis.reportEvent(self.reporter, idXp, "Emulator", "closed")
        self._logger.info("Emulator has finished.")        
        

    def __prepareAnalysis(self, commandLineParser):
        """Configures the class attributed through
        parameters stored in the command line parser.
        Returns the configuration
        """

        if commandLineParser is None:
            raise Exception("Cannot build the analysis configuration if no commandLineParser is provided")

        analysisOptions = commandLineParser.manualOptions

        if not 'apks' in analysisOptions.keys():
            raise Exception("The apks configuration entry is missing.")

        apkFiles = []
        for apkFile in analysisOptions['apks'].split(","):
            if apkFile is not None and len(apkFile)>0:
                # check the apk exists and is readable
                if not os.path.isfile(apkFile):
                    raise Exception("The apkFile {0} is not a file, we cannot prepare the analysis.".format(apkFile))
                if not os.access(apkFile, os.R_OK):
                    raise Exception("The apkFile {0} cannot be read, check the permissions.".format(apkFile))
                apkFiles.append(apkFile)

        analysisName = None
        if 'analysisname' in analysisOptions.keys():
            analysisName = analysisOptions['analysisname']

        maxNumberOfEmulators = 1
        if 'maxnumberofemulators' in analysisOptions.keys():
            try:
                maxNumberOfEmulators = int(analysisOptions['maxnumberofemulators'])
            except:
                raise Exception("'MaxNumberOfEmulators' in the configuration must be an interger.")            

        prepareAPKs = []
        if 'prepareapks' in analysisOptions.keys():
            for prepareAPK in analysisOptions['prepareapks'].split(","):
                if prepareAPK is not None and len(prepareAPK)>0:
                    # check the apk exists and is readable
                    if not os.path.isfile(prepareAPK):
                        raise Exception("The prepareAPK {0} is not a file, we cannot prepare the analysis.".format(prepareAPK))
                    if not os.access(prepareAPK, os.R_OK):
                        raise Exception("The prepareAPK {0} cannot be read, check the permissions.".format(prepareAPK))
                    prepareAPKs.append(prepareAPK)
            
        self._logger.debug("Configure the manual analysis.")        
        analysis = ManualAnalysisConfiguration(apkFiles, name=analysisName, maxNumberOfEmulators=maxNumberOfEmulators, prepareAPKs=prepareAPKs)

        return analysis

    def __str__(self):
        """toString method"""
        lines = [
            "---------------",
            "Manual Analysis",
            "---------------",
            str(self.mainConfiguration),
            str(self.analysisConfiguration),
            str(self.reportingConfiguration),
            "---------------"
        ]
        return '\n'.join(lines) 
        
    @property
    def analysisConfiguration(self):
        """The configuration of the analysis
        """
        return self.__analysisConfiguration

    @analysisConfiguration.setter
    def analysisConfiguration(self, configuration):
        self.__analysisConfiguration = configuration
